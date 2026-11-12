from dataclasses import replace
from datetime import UTC, datetime, timedelta
import json

import pytest
import yaml

from depot import publication
from depot.catalog import build
from depot.cli import main
from depot.config import Config, Target, load_manifest
from depot.errors import DepotError
from depot.service import Depot
from depot.storage import dataset_lock
from depot.validation import fingerprint, validate_package


def edit_manifest(config, dataset_id="example", **changes):
    path = config.registry / f"{dataset_id}.yaml"
    manifest = yaml.safe_load(path.read_text())
    manifest.update(changes)
    path.write_text(yaml.safe_dump(manifest))


def fake_publish(config, manifest, version, staged, expected, on_saved=None):
    if on_saved:
        on_saved("a" * 40)
    return {
        "commit": "a" * 40,
        "target": str(config.targets["prospects"].root / manifest["id"]),
        "clone_url": "ria+file:///private/test-store#~" + manifest["id"],
        "verified": True,
    }


def test_registry_and_configuration(config, register, tmp_path):
    register()
    assert load_manifest(config, "example")["schema_version"] == 1
    path = tmp_path / "depot.toml"
    path.write_text(
        'schema_version=1\nregistry="registry"\nwebsite="website"\nstate="state"\n'
        'staging="staging"\nworkspace="workspace"\nsource_roots=["prospectors"]\n'
        '[targets.prospects]\nlayer="02_prospects"\npath="goldmine/02_prospects"\n'
    )
    assert Config.load(path).registry == config.registry
    with pytest.raises(DepotError, match="disjoint"):
        replace(config, workspace=config.website / "workspace").check()


@pytest.mark.parametrize(
    "changes,code",
    [
        ({"schema_version": 2}, "invalid_registry"),
        ({"extra": "ignored?"}, "invalid_registry"),
        (
            {"destination": {"layer": "02_prospects", "target": "unknown"}},
            "unauthorized_destination",
        ),
        (
            {"destination": {"layer": "03_refined", "target": "prospects"}},
            "unauthorized_destination",
        ),
        ({"source": {"prospector": "fixture", "releases": "/not/allowed"}}, "unsafe_path"),
        ({"versions": {"pattern": "["}}, "invalid_registry"),
        ({"destination": {"layer": "03_refined", "target": "refined"}}, "invalid_registry"),
    ],
)
def test_registry_rejections(config, register, changes, code):
    register()
    edit_manifest(config, **changes)
    with pytest.raises(DepotError) as error:
        load_manifest(config, "example")
    assert error.value.code == code


def test_fetch_validate_and_receipts(config, register):
    release, _ = register()
    before = fingerprint(release)
    depot = Depot(config)
    assert depot.fetch("example", "v1")["status"] == "fetched"
    assert fingerprint(release) == before
    assert depot.validate("example", "v1")["validation"]["valid"]
    assert [r["status"] for r in depot.receipts("example")] == ["fetched", "validated"]


@pytest.mark.parametrize("version", ["../v1", "/v1", "v1/child", "bad", "-v1"])
def test_versions_cannot_escape(config, register, version):
    register()
    with pytest.raises(DepotError) as error:
        Depot(config).fetch("example", version)
    assert error.value.code == "invalid_version"


@pytest.mark.parametrize(
    "resource_path",
    ["../outside.csv", "/etc/passwd", "https://example.org/data.csv", "file:data.csv"],
)
def test_reject_nonlocal_resources(config, register, resource_path):
    release, manifest = register()
    package = json.loads((release / "datapackage.json").read_text())
    package["resources"][0]["path"] = resource_path
    (release / "datapackage.json").write_text(json.dumps(package))
    with pytest.raises(DepotError) as error:
        validate_package(release, manifest["checks"])
    assert error.value.code == "unsafe_resource"


@pytest.mark.parametrize(
    "fault,code",
    [
        ("symlink", "unsafe_path"),
        ("missing", "missing_resource"),
        ("empty", "empty_resource"),
        ("partial", "incomplete_release"),
        ("metadata", "missing_metadata"),
        ("schema_url", "unsafe_resource"),
        ("invalid_data", "invalid_package"),
        ("no_rows", "insufficient_rows"),
    ],
)
def test_package_failures(config, register, fault, code):
    release, manifest = register()
    data = release / "data.csv"
    package = json.loads((release / "datapackage.json").read_text())
    if fault == "symlink":
        data.unlink()
        data.symlink_to("/etc/passwd")
    elif fault == "missing":
        data.unlink()
    elif fault == "empty":
        data.write_text("")
    elif fault == "partial":
        (release / "download.part").write_text("unfinished")
    elif fault == "metadata":
        del package["title"]
    elif fault == "schema_url":
        package["resources"][0]["schema"] = "https://example.org/schema.json"
    elif fault == "invalid_data":
        data.write_text("id,value\n1,not-an-integer\n")
    elif fault == "no_rows":
        data.write_text("id,value\n")
    (release / "datapackage.json").write_text(json.dumps(package))
    with pytest.raises(DepotError) as error:
        validate_package(release, manifest["checks"])
    assert error.value.code == code


@pytest.mark.parametrize("where", ["source", "stage"])
def test_mutation_rejected(config, register, where):
    release, _ = register()
    depot = Depot(config)
    depot.fetch("example", "v1")
    depot.validate("example", "v1")
    directory = release if where == "source" else config.staging / "example/v1"
    (directory / "data.csv").write_text("id,value\n1,99\n")
    with pytest.raises(DepotError) as error:
        depot.push("example", "v1")
    assert error.value.code == "version_conflict"
    assert depot.receipts("example")[-1]["status"] == "failed"


def test_policy_change_invalidates_validation(config, register):
    register()
    depot = Depot(config)
    depot.fetch("example", "v1")
    depot.validate("example", "v1")
    edit_manifest(config, checks={"required_fields": ["name", "license"], "nonempty": True})
    with pytest.raises(DepotError) as error:
        depot.push("example", "v1")
    assert error.value.code == "not_validated"


def test_push_requires_validation(config, register):
    register()
    depot = Depot(config)
    depot.fetch("example", "v1")
    with pytest.raises(DepotError) as error:
        depot.push("example", "v1")
    assert error.value.code == "not_validated"


def test_idempotency_and_catalogue_recovery(config, register, monkeypatch):
    register()
    calls = []

    def publish(*args, **kwargs):
        calls.append(args)
        return fake_publish(*args, **kwargs)

    monkeypatch.setattr(publication, "publish", publish)
    depot = Depot(config)
    assert depot.sync()[0]["status"] == "success"
    assert not (config.website / "index.qmd").exists()
    # Rendering can be repeated from receipts without touching DataLad publication.
    build(config)
    first = (config.website / "index.qmd").read_bytes()
    assert depot.sync()[0]["status"] == "unchanged"
    build(config)
    assert (config.website / "index.qmd").read_bytes() == first
    assert len(calls) == 1
    assert len([r for r in depot.receipts("example") if r["status"] == "success"]) == 1


def test_invalid_release_retains_catalogue(config, register, monkeypatch):
    register()
    monkeypatch.setattr(publication, "publish", fake_publish)
    depot = Depot(config)
    depot.sync()
    build(config)
    original = (config.website / "index.qmd").read_bytes()
    register(version="v2", bad=True)
    results = depot.sync()
    assert results[-1]["status"] == "failed"
    build(config)
    assert (config.website / "index.qmd").read_bytes() == original
    assert "v2" not in (config.website / "datasets/example.qmd").read_text()


def test_sync_isolates_registry_and_package_failures(config, register, monkeypatch):
    register("broken", bad=True)
    register("good")
    register("malformed")
    edit_manifest(config, "malformed", schema_version=5)
    monkeypatch.setattr(publication, "publish", fake_publish)
    results = Depot(config).sync()
    assert {row["dataset_id"]: row["status"] for row in results} == {
        "broken": "failed",
        "good": "success",
        "malformed": "failed",
    }
    assert Depot(config).receipts("malformed")[-1]["error"]["code"] == "invalid_registry"
    assert [row["dataset_id"] for row in build(config)] == ["good"]


def test_missing_release_is_noop(config, register):
    release, _ = register()
    import shutil

    shutil.rmtree(release)
    assert Depot(config).sync() == [{"dataset_id": "example", "status": "no_new_release"}]


def test_failed_publication_and_safe_errors(config, register, monkeypatch):
    register()

    def failure(*args, **kwargs):
        raise RuntimeError("token=secret https://private:password@host/path")

    monkeypatch.setattr(publication, "publish", failure)
    results = Depot(config).sync()
    assert results[0]["status"] == "failed"
    assert "secret" not in json.dumps(Depot(config).receipts("example"))
    assert build(config) == []


def test_catalogue_visibility_privacy_escaping_and_removal(config, register, monkeypatch):
    register()
    edit_manifest(config, title='<script>alert("x")</script> {{< include /private/file >}}')
    monkeypatch.setattr(publication, "publish", fake_publish)
    Depot(config).sync()
    build(config)
    public = (config.website / "datasets/example.qmd").read_text()
    assert str(config.state.parent) not in public
    assert "private/test-store" not in public
    assert "<script>" not in public and "{{<" not in public
    assert "&lt;script&gt;" in public
    assert "git checkout --detach " + "a" * 40 in public
    assert "$&#123;DEPOT_STORE&#125;" in public
    unrelated = config.website / "datasets/handwritten.qmd"
    unrelated.write_text("Keep this.")
    edit_manifest(config, catalogue={"visible": False, "audience": "private"})
    assert build(config) == []
    assert not (config.website / "datasets/example.qmd").exists()
    assert unrelated.exists()


def test_catalogue_uses_verified_layer_not_current_target_label(config, register, monkeypatch):
    register()
    monkeypatch.setattr(publication, "publish", fake_publish)
    Depot(config).sync()
    # Changing an operator's label must not promote an already published release.
    edit_manifest(
        config,
        destination={"layer": "03_refined", "target": "prospects"},
        policy={"mode": "automatic", "approved_dates": ["2099-01-01"]},
    )
    changed = replace(
        config, targets={"prospects": Target("03_refined", config.targets["prospects"].root)}
    )
    from depot.catalog import public_entries

    assert public_entries(changed)[0]["layer"] == "02_prospects"


def test_refined_schedule(config, register, monkeypatch):
    register()
    tomorrow = (datetime.now(UTC) + timedelta(days=1)).date().isoformat()
    edit_manifest(
        config,
        destination={"layer": "03_refined", "target": "refined"},
        policy={"mode": "automatic", "approved_dates": [tomorrow]},
    )
    monkeypatch.setattr(
        publication,
        "publish",
        lambda *args, **kwargs: pytest.fail("Window must precede publication."),
    )
    results = Depot(config).sync()
    assert results[0]["error"]["code"] == "release_window_closed"


def test_dataset_lock(config, register):
    register()
    depot = Depot(config)
    with dataset_lock(config.state / "example/lock"), pytest.raises(DepotError) as error:
        depot.fetch("example", "v1")
    assert error.value.code == "dataset_locked"
    depot.fetch("example", "v1")


def test_cli_failure_exit_and_structured_output(config, register, monkeypatch, capsys):
    register(bad=True)
    monkeypatch.setattr(Config, "load", lambda path: config)
    assert main(["--json", "sync"]) == 1
    results = json.loads(capsys.readouterr().out)
    assert results[0]["status"] == "failed"
    assert (config.website / "index.qmd").exists()


def test_cli_rich_success_output(config, register, monkeypatch, capsys):
    register()
    monkeypatch.setattr(Config, "load", lambda path: config)
    monkeypatch.setattr(publication, "publish", fake_publish)
    for operation, status in (
        ("fetch", "fetched"),
        ("validate", "validated"),
        ("push", "success"),
    ):
        assert main([operation, "example", "v1"]) == 0
        assert status in capsys.readouterr().out
