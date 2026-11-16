"""Create a synthetic Prospector and isolated configuration outside the repository."""

import argparse
import json
from pathlib import Path
import shutil

from depot.catalog import build
from depot.config import Config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="An empty directory outside this repository.")
    args = parser.parse_args()
    root = args.root.resolve()
    repository = Path(__file__).resolve().parents[1]
    if root.is_relative_to(repository) or repository.is_relative_to(root):
        parser.error("Choose a demonstration root outside the website repository.")
    if root.exists() and any(root.iterdir()):
        parser.error("Demonstration root must be empty; no files have been changed.")
    release = root / "prospectors/example/data/outputs/releases/v1"
    release.mkdir(parents=True)
    (release / "data.csv").write_text("id,value\n1,42\n")
    (release / "datapackage.json").write_text(
        json.dumps(
            {
                "name": "example",
                "title": "Synthetic observations",
                "description": "A small reproducible Depot demonstration.",
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
            },
            indent=2,
        )
        + "\n"
    )
    (root / "registry").mkdir()
    shutil.copyfile(repository / "registry/example.yaml", root / "registry/example.yaml")
    shutil.copyfile(repository / "examples/depot.toml", root / "depot.toml")
    # The demo is an isolated copy of the same unified site and Manual.
    ignore = shutil.ignore_patterns(
        ".quarto", "site_libs", "*_files", "*.html", ".ipynb_checkpoints", "__pycache__"
    )
    for directory in ("notebooks", "src", "scripts", "examples", "tests"):
        shutil.copytree(repository / directory, root / directory, ignore=ignore)
    shutil.copy2(repository / "README.md", root / "README.md")
    # Drop any published snapshot copied from the real installation. The copied
    # Manual stays, while the synthetic registry supplies the demo catalogue.
    shutil.rmtree(root / "notebooks/datasets", ignore_errors=True)
    build(Config.load(root / "depot.toml"))
    print(f"Synthetic configuration created: {root / 'depot.toml'}")
    print("Run depot --config CONFIG fetch example v1, validate example v1, then push example v1.")
    print(
        f"Run depot --config CONFIG catalog build, then {root / 'scripts/render-isolated'} --profile authoring."
    )


if __name__ == "__main__":
    main()
