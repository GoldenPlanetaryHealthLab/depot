from dataclasses import replace
import shutil

import pytest
import yaml

from depot import publication
from depot.config import Config, Target, binding, load_manifest
from depot.errors import DepotError
from depot.validation import fingerprint


def test_default_view_is_populated_independent_and_writable(config, register):
    release, manifest = register()
    original = fingerprint(release)
    (release / "data.csv").chmod(0o444)
    access = publication.materialize(config, manifest, "v1", release, original)
    view = config.targets["prospects"].root / "example.data/releases/v1"
    assert access == {
        "mode": "unlocked",
        "populated": True,
        "path": str(view),
        "relative_path": "example.data/releases/v1",
    }
    assert fingerprint(view) == original
    assert not (view / "data.csv").is_symlink()
    assert (view / "data.csv").stat().st_mode & 0o200
    assert (view / "data.csv").stat().st_ino != (release / "data.csv").stat().st_ino
    (view / "data.csv").write_text("personal edits\n")
    assert fingerprint(release) == original
    with pytest.raises(DepotError) as error:
        publication.materialize(config, manifest, "v1", release, original)
    assert error.value.code == "access_conflict"
    assert (view / "data.csv").read_text() == "personal edits\n"


def test_locked_default_and_dataset_override(config, register):
    release, manifest = register()
    locked = replace(
        config,
        targets={
            **config.targets,
            "prospects": replace(config.targets["prospects"], access="locked"),
        },
    )
    expected = fingerprint(release)
    assert publication.materialize(locked, manifest, "v1", release, expected) == {
        "mode": "locked",
        "populated": False,
    }
    assert not locked.targets["prospects"].root.exists()
    manifest["destination"]["access"] = "unlocked"
    assert publication.materialize(locked, manifest, "v1", release, expected)["populated"]
    manifest["destination"]["access"] = "locked"
    publication.materialize(locked, manifest, "v1", release, expected)
    assert (locked.targets["prospects"].root / "example.data/releases/v1/data.csv").is_file()


def test_failed_copy_is_atomic_and_retryable(config, register, monkeypatch):
    release, manifest = register()
    expected = fingerprint(release)
    real_copytree = shutil.copytree

    def fail_copy(source, destination, **kwargs):
        destination.mkdir()
        (destination / "data.csv").write_text("partial")
        raise OSError("Synthetic disk failure")

    monkeypatch.setattr(publication.shutil, "copytree", fail_copy)
    with pytest.raises(OSError, match="disk failure"):
        publication.materialize(config, manifest, "v1", release, expected)
    root = config.targets["prospects"].root / "example.data/releases"
    assert not (root / "v1").exists()
    assert not list(root.glob(".populate-*"))
    monkeypatch.setattr(publication.shutil, "copytree", real_copytree)
    assert publication.materialize(config, manifest, "v1", release, expected)["populated"]


def test_materialization_rejects_redirected_view(config, register):
    release, manifest = register()
    target = config.targets["prospects"].root
    other = target / "other"
    other.mkdir(parents=True)
    (target / "example.data").symlink_to(other, target_is_directory=True)
    with pytest.raises(DepotError) as error:
        publication.materialize(config, manifest, "v1", release, fingerprint(release))
    assert error.value.code == "unsafe_path"
    assert not list(other.iterdir())


def test_access_policy_does_not_invalidate_content_validation(config, register):
    _, _ = register()
    manifest = load_manifest(config, "example")
    original = binding(config, manifest)
    manifest["destination"]["access"] = "locked"
    assert binding(config, manifest) == original
    path = config.registry / "example.yaml"
    path.write_text(yaml.safe_dump(manifest))
    assert load_manifest(config, "example")["destination"]["access"] == "locked"
    manifest["destination"]["access"] = "unknown"
    path.write_text(yaml.safe_dump(manifest))
    with pytest.raises(DepotError, match="schema"):
        load_manifest(config, "example")


def test_target_access_configuration(config, tmp_path):
    path = tmp_path / "access.toml"
    text = (
        'schema_version=1\nregistry="registry"\nwebsite="website"\nstate="state"\n'
        'staging="staging"\nworkspace="workspace"\nsource_roots=["prospectors"]\n'
        '[targets.prospects]\nlayer="02_prospects"\npath="goldmine/02_prospects"\n'
    )
    path.write_text(text)
    assert Config.load(path).targets["prospects"].access == "unlocked"
    path.write_text(text + 'access="locked"\n')
    assert Config.load(path).targets["prospects"].access == "locked"
    path.write_text(text + 'access="typo"\n')
    with pytest.raises(DepotError, match="access"):
        Config.load(path)
    with pytest.raises(DepotError, match="access"):
        replace(
            config, targets={"prospects": Target("02_prospects", tmp_path, access=True)}
        ).check()
