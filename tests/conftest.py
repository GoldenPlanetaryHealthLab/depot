import json
import shutil

import pytest
import yaml

from depot.config import Config, Target


@pytest.fixture
def config(tmp_path):
    result = Config(
        registry=tmp_path / "registry",
        website=tmp_path / "website",
        state=tmp_path / "state",
        staging=tmp_path / "staging",
        workspace=tmp_path / "workspace",
        source_roots=(tmp_path / "prospectors",),
        targets={
            "prospects": Target("02_prospects", tmp_path / "goldmine/02_prospects"),
            "refined": Target("03_refined", tmp_path / "goldmine/03_refined"),
        },
    )
    result.registry.mkdir()
    result.website.mkdir()
    result.check()
    return result


@pytest.fixture
def register(config):
    def create(dataset_id="example", version="v1", bad=False):
        source = config.source_roots[0] / dataset_id / "data/outputs/releases"
        manifest = {
            "schema_version": 1,
            "id": dataset_id,
            "title": "Synthetic observations",
            "description": "Small synthetic data for tests.",
            "source": {"prospector": "fixture-prospector", "releases": str(source)},
            "destination": {"layer": "02_prospects", "target": "prospects"},
            "versions": {"pattern": r"v[0-9]+"},
            "policy": {"mode": "automatic"},
            "checks": {
                "required_fields": ["name", "title", "description"],
                "nonempty": True,
                "minimum_rows": 1,
            },
            "catalogue": {"visible": True, "audience": "Lab developers; synthetic data."},
        }
        (config.registry / f"{dataset_id}.yaml").write_text(yaml.safe_dump(manifest))
        release = source / version
        release.mkdir(parents=True)
        (release / "data.csv").write_text("id,value\n1," + ("bad" if bad else "42") + "\n")
        package = {
            "name": dataset_id,
            "title": "Synthetic observations",
            "description": "Test fixture.",
            "resources": [
                {
                    "name": "observations",
                    "path": "data.csv",
                    "schema": {
                        "fields": [
                            {"name": "id", "type": "integer"},
                            {"name": "value", "type": "integer"},
                        ]
                    },
                }
            ],
        }
        (release / "datapackage.json").write_text(json.dumps(package))
        return release, manifest

    return create


@pytest.fixture
def datalad_tools():
    missing = [tool for tool in ("datalad", "git-annex", "git") if not shutil.which(tool)]
    if missing:
        pytest.skip(
            "Unverified publication: integration prerequisites unavailable: " + ", ".join(missing)
        )
