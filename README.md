# Depot

Depot validates immutable Prospector releases, publishes accepted data through
the DataLad CLI, and generates a small Quarto catalogue. A version is advertised
only after a fresh clone retrieves and validates the published files.

This milestone supports local filesystem RIA destinations for `02_prospects`
and `03_refined`. It does not deploy a live Goldmine target or activate scheduling.

## Setup

Prerequisites: Python 3.14, uv, Git with a configured author identity, DataLad,
git-annex, and Quarto 1.9 or newer. DataLad and git-annex are external command-line
tools and must be on `PATH`; they are not imported by the Python application.

```sh
uv sync --locked
uv run depot --help
datalad --version
git annex version
quarto --version
```

`uv.lock` records the Python dependency resolution. The existing `spack.yaml`
and `spack.lock` do not supply all the external publication tools. The source
package retains the existing Flit build system.

## Prove a synthetic release

Create the demonstration in a new, empty directory outside the website checkout:

```sh
uv run python scripts/demo.py /tmp/depot-example
export DEPOT_CONFIG=/tmp/depot-example/depot.toml
uv run depot fetch example v1
uv run depot validate example v1
uv run depot push example v1
uv run depot catalog build
quarto render /tmp/depot-example/website
```

Expected statuses are `fetched`, `validated`, `success`, and `catalogued`. `push`
performs fresh-clone verification before recording `success`. The rendered
demonstration is `/tmp/depot-example/website/_site/index.html`.

```sh
uv run depot sync
uv run depot --json receipts example
```

The repeat sync reports `unchanged` without another publication. An empty or
absent source releases directory reports `no_new_release` successfully.
Rejected attempts appear in internal receipts and cause `sync` to exit 1;
other datasets and versions are still processed. Sync rebuilds catalogue source
pages even when a dataset fails. Render the site separately afterward.

## Registry and configuration

Register a dataset by adding one reviewed `registry/ID.yaml` manifest. Commands
validate it against `src/depot/schemas/registry-v1.schema.json`. Unknown fields,
unauthorized destinations, and invalid IDs or versions are rejected.

The example manifest is:

```yaml
schema_version: 1
id: example
title: Synthetic example
description: Small synthetic observations for demonstrating publication.
source:
  prospector: fixture-prospector
  releases: ../prospectors/example/data/outputs/releases
destination:
  layer: 02_prospects
  target: prospects
versions:
  pattern: 'v[0-9]+'
policy:
  mode: automatic
checks:
  required_fields: [name, title, description]
  nonempty: true
  minimum_rows: 1
catalogue:
  visible: true
  audience: Lab developers testing the release workflow; synthetic data only.
```

Relative source paths resolve from the registry directory. Releases contain
`VERSION/datapackage.json` and every declared local resource. Depot never edits
or executes Prospector output.

Copy `examples/depot.toml` to an internal configuration location and adjust its
paths. Relative configuration paths resolve from that file's directory:

```toml
schema_version = 1
registry = "registry"
website = "website"
source_roots = ["prospectors"]
state = "state"
staging = "staging"
workspace = "workspace"

[targets.prospects]
layer = "02_prospects"
path = "goldmine/02_prospects"

[targets.refined]
layer = "03_refined"
path = "goldmine/03_refined"
```

For the actual checkout, `website` points to the repository root and `registry`
may point to its reviewed registry directory. Source, state, staging, workspace,
and target roots must be disjoint from one another and from the website. Keep
internal configuration outside the public repository. `--config FILE` overrides
`DEPOT_CONFIG`; without either, Depot looks for `depot.toml`.

Layers come from reviewed policy and the configured target allow-list, never
from directory names. Prospects publish automatically. Refined manifests must
also specify `policy.approved_dates`, a list of UTC dates such as `["2027-01-15"]`.
Schedules and extra package checks are standing policy, not per-version prompts.

Sync processes versions in natural order (`v2` before `v10`); the catalogue
selects the greatest verified version using that ordering. This is not SemVer:
choose a naming scheme whose natural order represents release order, such as
zero-padded dates or `vNUMBER`.

## Validation and recovery

Depot validates its registry contract, then the Frictionless descriptor and
resource contents. Policy can require metadata fields, nonempty files, and
minimum row counts. Resources must be local files; schemas, dialects, and
controls must be inline objects. Remote and inline-data resources are outside
this milestone. Source symlinks, traversal, special files, reserved Git control
files, and `.part`, `.partial`, or `.tmp` files are rejected.

A fingerprint hashes sorted relative filenames, byte sizes, and SHA-256 content
hashes. Fetch copies to a temporary directory, compares source and copied
content, then promotes the staging snapshot. Different bytes or source identity
under an existing version are conflicts. Validation binds the candidate to its
manifest and configured destination. Policy changes require validation again;
push also checks source and staging fingerprints.

The Prospector must expose a completed release directory atomically and then
leave it immutable. Depot can detect missing, invalid, unfinished, or changing
files; it cannot infer that a producer intended to add more valid rows later.

Operational state stays outside the website:

```text
STATE/ID/versions/VERSION.json       # source identity, fingerprint, validation, commit
STATE/ID/receipts/TIMESTAMP-UUID.json # append-only attempt history
STATE/ID/lock                        # Linux flock for overlapping operations
STAGING/ID/VERSION/                  # Depot-owned import
WORKSPACE/ID/releases/VERSION/       # DataLad-managed history and content
TARGET_ROOT/ID/                      # RIA store, not a populated working tree
```

Receipts include dataset/version, source fingerprint and identity, validation,
commit when available, target, verification, timestamp, and error. Only a
verified push creates `status: success`. Failed attempts preserve previous
successes. Command errors identify the operation and exit code; raw subprocess
output is withheld because it can contain credentials or private paths.

An interrupted push may have saved or transferred data. Retry the same
validated candidate: its immutable workspace content and commit are reused,
then publication and retrieval are retried. The success receipt is the
publication boundary. A later catalogue or Quarto failure can be repaired by
rerunning `catalog build` and `quarto render` without publishing again. Retain
state and receipt history rather than treating them as disposable cache.

## Retrieve published data

Depot uses one local RIA store per dataset beneath the configured target root.
It creates no parent Goldmine dataset or registered subdatasets. The publisher's
`goldmine` sibling depends on `goldmine-storage`, which transfers annexed bytes.
Verification explicitly retrieves from that storage sibling, excluding
publisher-local content as a source.

For the synthetic demonstration:

```sh
export DEPOT_STORE=/tmp/depot-example/goldmine/02_prospects/example
datalad clone "ria+file://${DEPOT_STORE}#~example" /tmp/depot-retrieved
cd /tmp/depot-retrieved
git checkout --detach COMMIT_FROM_SUCCESS_RECEIPT
datalad get --source goldmine-storage releases/v1
cat releases/v1/datapackage.json
cat releases/v1/data.csv
```

Use the `commit` in the successful receipt. Stagecoach can use the same
clone/checkout/get sequence. Public detail pages provide the commit and release
path; an operator supplies `DEPOT_STORE`. Package metadata is available after
retrieval rather than copied wholesale into the public site.

The layout follows DataLad's documented
[RIA publication interface](https://docs.datalad.org/en/stable/generated/man/datalad-create-sibling-ria.html).
Cross-user permissions, group ownership, ACLs, shared-filesystem locking, quotas,
and access from compute/client nodes require a separate shared-storage trial
before configuring a live Goldmine destination. Do not run git-annex directly
inside a RIA store.

## Manual source and website

`notebooks/*.qmd` are the source of truth for Python modules in `src/depot`.
They use Quarto Manuals' `quarto-emit` extension; vendoring and the portable
provenance change are documented in
`_extensions/TinasheMTapera/quarto-emit/PROVENANCE.md`. Edit manual code blocks,
then explicitly emit:

```sh
QUARTO_EMIT=1 quarto render
uv run pytest
git diff
```

Ordinary rendering displays the manual without writing Python. Code blocks
do not execute ingestion or analytical notebooks. A test checks exact agreement
between manual blocks and emitted source.

The generator writes `index.qmd` and `datasets/ID.qmd` from successful receipts
and selected metadata. It excludes operational paths/errors, hidden datasets,
and failed releases. It removes only previously tracked generated pages when
visibility changes. Quarto output goes to ignored `docs/` for local review;
deployment is a separate action.

## Tests

```sh
uv run pytest -q
uv run ruff check src tests scripts
uv run ruff format --check src tests scripts
quarto render
```

Unit tests cover registry contracts, resource validation, path safety, content
conflicts, policy changes, schedules, receipts, catalogue privacy, idempotency,
locks, and failure isolation. Integration tests use synthetic data and temporary
local RIA stores, including fresh retrieval, failed push/retrieval recovery,
and preserving the prior catalogue after rejection.

Integration tests skip clearly when DataLad, git-annex, or Git is missing; a skip
does not verify publication. `pytest -m 'not integration'` runs unit tests only.
See `VALIDATION.md` for observed results and environment-specific limitations.

## Proposed FASRC scheduling — inactive

`scripts/sync.sbatch.example` is a proposed manual batch entry point. Set project
and configuration paths, review resources and tool activation, and test manually
before scheduling. It renders catalogue updates even if one dataset fails,
while preserving the failed sync exit code.

A future scrontab entry could be:

```text
#SCRON --partition=REVIEW_PARTITION
#SCRON --account=REVIEW_ACCOUNT
#SCRON --cpus-per-task=1
#SCRON --mem=4G
#SCRON --time=01:00:00
#SCRON --open-mode=append
0 * * * * DEPOT_PROJECT=/path/to/depot DEPOT_CONFIG=/path/to/internal/depot.toml bash /path/to/depot/scripts/sync.sbatch.example
```

`#SCRON` lines supply resources; `#SBATCH` directives inside the script are
ignored by scrontab. Times follow the controller's timezone and queue delays.
Confirm local availability and partition/account settings against the
[FASRC guide](https://docs.rc.fas.harvard.edu/kb/scrontab/) and
[Slurm manual](https://slurm.schedmd.com/scrontab.html).
No schedule has been installed and no live Goldmine target configured.
