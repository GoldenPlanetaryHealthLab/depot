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
    updates = []
    depot = Depot(config, on_progress=updates.append)
    depot.fetch("example", "v1")
    depot.validate("example", "v1")
    receipt = depot.push("example", "v1")
    assert receipt["status"] == "success" and receipt["verified"]
    messages = [update.message for update in updates]
    for phase in (
        "Pushing release to publication storage",
        "Cloning published dataset for retrieval verification",
        "Retrieving published release from storage",
        "Publication and fresh retrieval verified",
    ):
        assert f"example v1: {phase}" in messages
    assert receipt["fingerprint"] == before == fingerprint(release)
    workspace = config.workspace / "example"
    view = config.targets["prospects"].root / "example.data/releases/v1"
    assert receipt["access"]["mode"] == "unlocked" and receipt["access"]["populated"]
    assert fingerprint(view) == before
    assert not (workspace / "releases/v1/data.csv").is_symlink()
    assert not (view / "data.csv").is_symlink()
    assert (view / "data.csv").stat().st_mode & 0o200
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


@pytest.mark.parametrize("failure_phase", ["retrieval", "materialization"])
def test_real_failed_verification_recovers(
    config, register, datalad_tools, monkeypatch, failure_phase
):
    register()
    depot = Depot(config)
    depot.fetch("example", "v1")
    depot.validate("example", "v1")
    real_command = publication.command
    real_materialize = publication.materialize

    def command(args, cwd=None):
        if args[:2] == ["datalad", "get"]:
            raise DepotError("command_failed", "Synthetic retrieval failure.")
        return real_command(args, cwd=cwd)

    if failure_phase == "retrieval":
        monkeypatch.setattr(publication, "command", command)
    else:

        def fail_materialization(*args, **kwargs):
            raise DepotError("operation_failed", "Synthetic population failure.")

        monkeypatch.setattr(publication, "materialize", fail_materialization)
    with pytest.raises(DepotError):
        depot.push("example", "v1")
    assert build(config) == []
    assert not any(r["status"] == "success" for r in depot.receipts("example"))
    assert depot.receipts("example")[-1]["commit"]
    commit = real_command(["git", "rev-parse", "HEAD"], cwd=config.workspace / "example")
    monkeypatch.setattr(publication, "command", real_command)
    monkeypatch.setattr(publication, "materialize", real_materialize)
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


def test_real_locked_archive_can_gain_default_view_without_republishing(
    config, register, datalad_tools, monkeypatch
):
    from dataclasses import replace
    import shutil

    release, _ = register()
    locked = replace(
        config,
        targets={
            **config.targets,
            "prospects": replace(config.targets["prospects"], access="locked"),
        },
    )
    depot = Depot(locked)
    depot.fetch("example", "v1")
    depot.validate("example", "v1")
    archived = depot.push("example", "v1")
    workspace = config.workspace / "example"
    assert (workspace / "releases/v1/data.csv").is_symlink()
    assert archived["access"] == {"mode": "locked", "populated": False}
    view = config.targets["prospects"].root / "example.data/releases/v1"
    assert not view.exists()

    def no_publication(*args, **kwargs):
        pytest.fail("An existing verified release must not be republished")

    monkeypatch.setattr(publication, "publish", no_publication)
    unlocked = Depot(config)
    upgraded = unlocked.push("example", "v1")
    assert upgraded["status"] == "success"
    assert upgraded["commit"] == archived["commit"]
    assert fingerprint(view) == fingerprint(release)
    assert not (view / "data.csv").is_symlink()
    assert (view / "data.csv").stat().st_mode & 0o200
    assert unlocked.push("example", "v1")["status"] == "unchanged"
    shutil.rmtree(view)
    assert unlocked.push("example", "v1")["status"] == "unchanged"
    assert fingerprint(view) == fingerprint(release)
    build(config)
    page = (config.website / "datasets/example.qmd").read_text()
    assert "Use the data directly" in page
    assert "02_prospects/example.data/releases/v1/" in page
    assert str(config.targets["prospects"].root) not in page
    (view / "data.csv").write_text("user edits")
    with pytest.raises(DepotError) as error:
        unlocked.push("example", "v1")
    assert error.value.code == "access_conflict"
    assert (view / "data.csv").read_text() == "user edits"
    assert publication.command(["git", "rev-parse", "HEAD"], cwd=workspace) == archived["commit"]
