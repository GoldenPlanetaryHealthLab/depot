import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

import pandas as pd
import pytest

from depot import catalog


@pytest.mark.integration
def test_quarto_keeps_dataframe_values_literal(config, monkeypatch, tmp_path):
    if not shutil.which("quarto"):
        pytest.skip("Rendered catalogue verification requires Quarto.")
    data = pd.DataFrame.from_records(
        [
            {
                "id": "example",
                "title": '<script>alert("literal")</script> {{< include /private/file >}}',
                "description": "[download](javascript:alert(1)) **literal**",
                "layer": "02_prospects",
                "version": "v1",
                "published": "2026-11-13",
                "commit": "a" * 40,
                "prospector": "synthetic",
                "package_name": "example",
                "audience": "Synthetic test",
                "resources": [{"name": "**resource**", "files": 1, "bytes": 14}],
            }
        ]
    )
    monkeypatch.setattr(catalog, "catalogue_data", lambda _: data)
    catalog.build(config)
    (config.website / "_quarto.yml").write_text(
        "project:\n  type: website\n  output-dir: _site\n"
        "engine: markdown\nexecute:\n  enabled: false\n"
    )
    environment = {
        **os.environ,
        "XDG_CACHE_HOME": str(tmp_path / "xdg-cache"),
        "XDG_DATA_HOME": str(tmp_path / "xdg-data"),
        "XDG_RUNTIME_DIR": str(tmp_path / "xdg-runtime"),
    }
    # Quarto skips inputs beneath hidden ancestors such as the suite's .depot base.
    # Render the generated pages in an isolated, non-hidden project like the Manual helper.
    with TemporaryDirectory(prefix="depot-catalogue-render-") as temporary:
        website = Path(temporary) / "website"
        shutil.copytree(config.website, website)
        result = subprocess.run(
            ["quarto", "render"],
            check=False,
            cwd=website,
            env=environment,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        for relative in ("index.html", "datasets/example.html"):
            html = (website / "_site" / relative).read_text()
            assert '<script>alert("literal")</script>' not in html
            assert "&lt;script&gt;" in html
            assert 'href="javascript:' not in html
            assert "<strong>literal</strong>" not in html
            assert "**literal**" in html
        detail = (website / "_site/datasets/example.html").read_text()
        assert "**resource**" in detail
        assert "<strong>resource</strong>" not in detail


from dataclasses import replace
import json


@pytest.mark.integration
def test_catalogue_and_manual_share_the_site(config, monkeypatch, tmp_path):
    if not all(shutil.which(tool) for tool in ("quarto", "rsync")):
        pytest.skip("Unified site verification requires Quarto and rsync.")
    root = Path(__file__).resolve().parents[1]
    project = tmp_path / "project"
    ignore = shutil.ignore_patterns(".quarto", "site_libs", "__pycache__", ".ipynb_checkpoints")
    for directory in ("notebooks", "src", "scripts", "examples", "tests"):
        shutil.copytree(root / directory, project / directory, ignore=ignore)
    shutil.copy2(root / "README.md", project / "README.md")
    # Remove only the copied installation's generated snapshots, never its Manual.
    shutil.rmtree(project / "notebooks/datasets", ignore_errors=True)
    config = replace(config, website=project / "notebooks")
    data = pd.DataFrame.from_records(
        [
            {
                "id": "example",
                "title": "Example lab dataset",
                "description": "Synthetic catalogue entry",
                "layer": "02_prospects",
                "version": "v1",
                "published": "2026-11-13",
                "commit": "a" * 40,
                "prospector": "fixture",
                "package_name": "example",
                "audience": "Lab members",
                "resources": [{"name": "observations", "files": 1, "bytes": 14}],
            }
        ]
    )
    monkeypatch.setattr(catalog, "catalogue_data", lambda _: data)
    manual = config.website / "overview.qmd"
    before = manual.read_bytes()
    quarto_before = (config.website / "_quarto.yml").read_bytes()

    def render():
        result = subprocess.run(
            ["bash", str(project / "scripts/render-isolated"), "--profile", "authoring"],
            check=False,
            cwd=project,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr

    catalog.build(config)
    render()
    index = (project / "docs/index.html").read_text()
    detail = (project / "docs/datasets/example.html").read_text()
    assert 'id="depot-catalogue"' in index
    assert "Example lab dataset" in index
    assert 'href="datasets/example.html"' in index
    assert "overview.html" in index and "Operator Manual" in index
    assert (project / "docs/overview.html").is_file()
    assert "depot-resources-example" in detail
    search = json.loads((project / "docs/search.json").read_text())
    assert any(item["href"].startswith("datasets/example.html") for item in search)
    assert any(item["href"].startswith("overview.html") for item in search)

    # Withdrawing a catalogue entry must retain the Manual and remove stale HTML.
    data = data.head(0)
    catalog.build(config)
    render()
    assert "No verified datasets are available yet." in (project / "docs/index.html").read_text()
    assert not (project / "docs/datasets/example.html").exists()
    assert manual.read_bytes() == before
    assert (config.website / "_quarto.yml").read_bytes() == quarto_before
    assert (project / "docs/overview.html").is_file()
