from io import StringIO
import json

import pytest
from rich.console import Console

from depot import cli, validation
from depot.cli import CLIProgress, main
from depot.config import Config
from depot.errors import DepotError
from depot.progress import ProgressUpdate
from depot.service import Depot
from depot.storage import dataset_lock
from depot.validation import validate_package


@pytest.mark.parametrize("resource_format", ["csv", "parquet"])
def test_validation_reports_resources_and_rows_without_changing_results(
    register, monkeypatch, resource_format
):
    release, manifest = register()
    (release / "data.csv").write_text("id,value\n" + "1,42\n" * 10_001)
    descriptor_path = release / "datapackage.json"
    descriptor = json.loads(descriptor_path.read_text())
    second = {**descriptor["resources"][0], "name": "second", "path": "second.csv"}
    descriptor["resources"].append(second)
    (release / "second.csv").write_text("id,value\n2,43\n")
    if resource_format == "parquet":
        import pyarrow as pa
        import pyarrow.parquet as pq

        for resource, ids, values in (
            (descriptor["resources"][0], [1] * 10_001, [42] * 10_001),
            (second, [2], [43]),
        ):
            resource["path"] = resource["path"].replace(".csv", ".parquet")
            resource["format"] = "parquet"
            pq.write_table(pa.table({"id": ids, "value": values}), release / resource["path"])
    descriptor_path.write_text(json.dumps(descriptor))
    modes = []
    original_validate = validation.Package.validate

    def observe_mode(package, *args, **kwargs):
        modes.append(kwargs["parallel"])
        return original_validate(package, *args, **kwargs)

    monkeypatch.setattr(validation.Package, "validate", observe_mode)
    parallel_updates = []
    expected = validate_package(release, manifest["checks"], on_progress=parallel_updates.append)
    assert ProgressUpdate("Validating 2 resources in parallel") in parallel_updates
    updates = []
    assert (
        validate_package(release, manifest["checks"], parallel=False, on_progress=updates.append)
        == expected
    )
    messages = [update.message for update in updates]
    assert messages.index("Loading resource 1/2: observations") < messages.index(
        "Checking resource 1/2: observations"
    )
    assert ProgressUpdate("Checking resource 1/2: observations", 10_000, unit="rows") in updates
    assert (
        ProgressUpdate("Finished checking resource 1/2: observations", 10_001, unit="rows")
        in updates
    )
    assert ProgressUpdate("Finished checking resource 2/2: second", 1, unit="rows") in updates
    assert messages[-1] == "Package validation passed"
    assert modes == [True, False]


@pytest.mark.parametrize("fault", ["schema", "minimum_rows"])
def test_progress_preserves_validation_failures(register, fault):
    release, manifest = register(bad=fault == "schema")
    if fault == "minimum_rows":
        (release / "data.csv").write_text("id,value\n")
    with pytest.raises(DepotError) as baseline:
        validate_package(release, manifest["checks"], parallel=False)
    updates = []
    with pytest.raises(DepotError) as observed:
        validate_package(release, manifest["checks"], on_progress=updates.append)
    assert observed.value.as_dict() == baseline.value.as_dict()
    assert "Package validation passed" not in [update.message for update in updates]


@pytest.mark.parametrize("invalid_reference", [False, True])
def test_foreign_keys_keep_sequential_checks_and_progress(register, invalid_reference):
    release, manifest = register()
    descriptor_path = release / "datapackage.json"
    descriptor = json.loads(descriptor_path.read_text())
    parent = descriptor["resources"][0]
    parent["schema"]["primaryKey"] = ["id"]
    descriptor["resources"].append(
        {
            "name": "children",
            "path": "children.csv",
            "schema": {
                "fields": parent["schema"]["fields"],
                "foreignKeys": [
                    {
                        "fields": ["id"],
                        "reference": {"resource": "observations", "fields": ["id"]},
                    }
                ],
            },
        }
    )
    descriptor_path.write_text(json.dumps(descriptor))
    (release / "children.csv").write_text(
        "id,value\n" + ("2" if invalid_reference else "1") + ",42\n"
    )
    updates = []
    if invalid_reference:
        with pytest.raises(DepotError) as failure:
            validate_package(release, manifest["checks"], on_progress=updates.append)
        assert "foreign-key" in failure.value.details["error_types"]
    else:
        assert validate_package(release, manifest["checks"], on_progress=updates.append)["valid"]
    assert ProgressUpdate("Validating 2 resources sequentially") in updates
    assert ProgressUpdate("Finished checking resource 2/2: children", 1, unit="rows") in updates


def test_batch_progress_is_literal_throttled_and_keeps_phase_transitions(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(cli, "monotonic", lambda: clock[0])
    output = StringIO()
    status = CLIProgress(console=Console(file=output, force_terminal=False, width=160))
    status.start()
    try:
        status(ProgressUpdate("Loading resource 1/1: [bold]literal[/bold]"))
        status(ProgressUpdate("Checking resource 1/1: observations", 0, unit="rows"))
        clock[0] = 1.0
        status(ProgressUpdate("Checking resource 1/1: observations", 10_000, unit="rows"))
        assert "10,000 rows" not in output.getvalue()
        clock[0] = 31.0
        status(ProgressUpdate("Checking resource 1/1: observations", 20_000, unit="rows"))
        status(ProgressUpdate("Finished checking resource 1/1: observations", 20_001, unit="rows"))
    finally:
        status.stop()
    text = output.getvalue()
    assert "[bold]literal[/bold]" in text
    assert "20,000 rows" in text and "20,001 rows" in text
    assert text.count("Checking resource") == 2
    assert "\x1b" not in text


def test_terminal_progress_uses_rich_live_display():
    output = StringIO()
    status = CLIProgress(console=Console(file=output, force_terminal=True, width=160))
    status.start()
    try:
        status(ProgressUpdate("Checking resource 3/99: observations", 50_000, unit="rows"))
        status.display.refresh()
    finally:
        status.stop()
    text = output.getvalue()
    assert "Checking resource 3/99: observations" in text
    assert "50,000 rows" in text
    assert "\x1b[?25h" in text  # Rich restores the cursor when the display stops.


def test_cli_shows_fetch_and_validation_progress(config, register, monkeypatch, capsys):
    register()
    monkeypatch.setattr(Config, "load", lambda path: config)
    assert main(["fetch", "example", "v1"]) == 0
    fetched = capsys.readouterr()
    assert "Copying release into staging" in fetched.err
    assert "Fingerprinted release files" in fetched.err
    assert "example v1" in fetched.err
    assert "fetched" in fetched.out
    assert main(["validate", "example", "v1"]) == 0
    validated = capsys.readouterr()
    assert "Validating 1 resources in parallel" in validated.err
    assert "Recording validation result" in validated.err
    assert "validated" in validated.out
    assert "Loading resource" not in validated.out


def test_cli_json_and_receipts_remain_progress_free(config, register, monkeypatch, capsys):
    register()
    monkeypatch.setattr(Config, "load", lambda path: config)
    for arguments in (
        ["--json", "fetch", "example", "v1"],
        ["--json", "validate", "example", "v1"],
        ["receipts", "example"],
    ):
        assert main(arguments) == 0
        captured = capsys.readouterr()
        assert isinstance(json.loads(captured.out), list)
        assert captured.err == ""


def test_cli_failure_keeps_dataset_and_version(config, register, monkeypatch, capsys):
    register()
    monkeypatch.setattr(Config, "load", lambda path: config)
    assert main(["--json", "validate", "example", "v1"]) == 1
    captured = capsys.readouterr()
    failure = json.loads(captured.out)[0]
    assert failure["dataset_id"] == "example" and failure["version"] == "v1"
    assert failure["error"]["code"] == "not_fetched"
    assert captured.err == ""


@pytest.mark.parametrize("json_mode", [False, True])
def test_interruption_cleans_up_without_recording_validation(
    config, register, monkeypatch, capsys, json_mode
):
    register()
    Depot(config).fetch("example", "v1")
    monkeypatch.setattr(Config, "load", lambda path: config)

    def interrupt(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr("depot.validation.Package.validate", interrupt)
    args = ["validate", "example", "v1"]
    assert main((["--json"] if json_mode else []) + args) == 130
    captured = capsys.readouterr()
    if json_mode:
        assert json.loads(captured.out)[0]["status"] == "interrupted"
        assert captured.err == ""
    else:
        assert "interrupted" in captured.out
        assert "Traceback" not in captured.err
    assert not any(
        receipt["status"] == "validated" for receipt in Depot(config).receipts("example")
    )
    with dataset_lock(config.state / "example/lock"):
        pass
