"""Create a synthetic Prospector and isolated configuration outside the repository."""

import argparse
import json
from pathlib import Path
import shutil


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
    (root / "website").mkdir()
    (root / "website/_quarto.yml").write_text(
        "project:\n  type: website\n  output-dir: _site\nwebsite:\n  title: Depot demonstration\n"
        "format: html\nexecute:\n  enabled: false\n"
    )
    print(f"Synthetic configuration created: {root / 'depot.toml'}")
    print("Run depot --config CONFIG fetch example v1, validate example v1, then push example v1.")
    print("Run depot --config CONFIG catalog build, then quarto render WEBSITE.")


if __name__ == "__main__":
    main()
