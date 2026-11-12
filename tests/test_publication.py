import pytest

from depot import publication
from depot.catalog import build
from depot.errors import DepotError
from depot.service import Depot
from depot.validation import fingerprint

pytestmark = pytest.mark.integration


def test_real_round_trip_idempotency_and_rejection(config, register, datalad_tools):
    release, _ = register()
    before = fingerprint(release)
    depot = Depot(config)
    depot.fetch("example", "v1")
    depot.validate("example", "v1")
    receipt = depot.push("example", "v1")
    assert receipt["status"] == "success" and receipt["verified"]
    assert receipt["fingerprint"] == before == fingerprint(release)
    workspace = config.workspace / "example"
    assert publication.command(
        ["git", "annex", "lookupkey", "releases/v1/data.csv"], cwd=workspace
    )
    commit = publication.command(["git", "rev-parse", "HEAD"], cwd=workspace)
    assert depot.push("example", "v1")["status"] == "unchanged"
    assert publication.command(["git", "rev-parse", "HEAD"], cwd=workspace) == commit
    register(version="v2")
    assert depot.sync()[-1]["status"] == "success"
    assert depot.push("example", "v1")["commit"] == commit
    build(config)
    original = (config.website / "index.qmd").read_bytes()
    register(version="v3", bad=True)
    assert any(r["status"] == "failed" for r in depot.sync())
    build(config)
    assert (config.website / "index.qmd").read_bytes() == original
    (release / "data.csv").write_text("id,value\n1,99\n")
    with pytest.raises(DepotError) as error:
        depot.fetch("example", "v1")
    assert error.value.code == "version_conflict"


def test_real_failed_verification_recovers(config, register, datalad_tools, monkeypatch):
    register()
    depot = Depot(config)
    depot.fetch("example", "v1")
    depot.validate("example", "v1")
    real_command = publication.command

    def command(args, cwd=None):
        if args[:2] == ["datalad", "get"]:
            raise DepotError("command_failed", "Synthetic retrieval failure.")
        return real_command(args, cwd=cwd)

    monkeypatch.setattr(publication, "command", command)
    with pytest.raises(DepotError):
        depot.push("example", "v1")
    assert build(config) == []
    assert not any(r["status"] == "success" for r in depot.receipts("example"))
    assert depot.receipts("example")[-1]["commit"]
    commit = real_command(["git", "rev-parse", "HEAD"], cwd=config.workspace / "example")
    monkeypatch.setattr(publication, "command", real_command)
    assert depot.push("example", "v1")["status"] == "success"
    assert real_command(["git", "rev-parse", "HEAD"], cwd=config.workspace / "example") == commit


def test_real_two_datasets_one_fails(config, register, datalad_tools):
    register("broken", bad=True)
    register("good")
    results = Depot(config).sync()
    assert {r["dataset_id"]: r["status"] for r in results} == {
        "broken": "failed",
        "good": "success",
    }
    assert build(config) == [{"dataset_id": "good", "status": "catalogued", "version": "v1"}]


def test_real_failed_push_does_not_publish_success(config, register, datalad_tools, monkeypatch):
    register()
    real_command = publication.command

    def command(args, cwd=None):
        if args[:2] == ["datalad", "push"]:
            raise DepotError("command_failed", "Synthetic destination outage.")
        return real_command(args, cwd=cwd)

    monkeypatch.setattr(publication, "command", command)
    depot = Depot(config)
    assert depot.sync()[0]["status"] == "failed"
    assert build(config) == []
    assert "success" not in [r["status"] for r in depot.receipts("example")]
    monkeypatch.setattr(publication, "command", real_command)
    assert depot.sync()[0]["status"] == "success"
