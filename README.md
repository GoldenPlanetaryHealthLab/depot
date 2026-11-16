# Depot

## 1. What Depot is for

Depot takes completed, immutable data releases from Prospectors, validates and
publishes them to approved storage through DataLad, and adds verified publications
to a browsable Quarto data catalogue. A dataset appears in the catalogue only after
Depot has published it, retrieved it in a fresh clone, and validated that retrieval.

The complete workflow is:

**Prepare a release → register the dataset → fetch → validate → push → build the
catalogue → render the catalogue website.**

| Input | What Depot produces |
|---|---|
| A Prospector release directory containing `datapackage.json` and its resources | A staged snapshot with a content fingerprint |
| A reviewed dataset registry YAML and installation configuration | Validated, versioned DataLad publication in an approved destination |
| Verified publication receipts | Catalogue source pages and resource tables, ready for Quarto rendering |

Depot is the lab's data visibility layer: the GitHub Pages landing page is the
data catalogue, and the rest of the same site is its operating Manual. Depot
consumes released data; the Prospector owns data preparation and scientific
transformations. This implementation supports local filesystem RIA destinations
for `02_prospects` and `03_refined`. Registering a dataset does not fetch or publish
it. Validation checks an already-fetched snapshot; it does not fetch implicitly.

Start with [setup](#setup), then follow [the real-data walkthrough](#add-data).
The [synthetic demonstration](#synthetic-demo) is optional and uses a separate
configuration. No schedule is installed automatically.

<a id="setup"></a>

## 2. Set up Depot

Run commands from the Depot checkout. Spack supplies Python 3.14; uv manages the
project's `.venv` and Python dependencies. Git with an author identity, DataLad,
git-annex, Quarto 1.9+, Bash, and rsync must also be available on `PATH`.

### Prepare the software environment

Initialize your site's Spack shell support if it is not already loaded:

```sh
source /path/to/spack/share/spack/setup-env.sh
```

Only when preparing or updating the Spack environment, install its dependencies:

```sh
spack -e . concretize --reuse
spack -e . install
```

For each working shell, activate the installed environment and select its Python:

```sh
spack env activate -d .
export UV_PYTHON="$PWD/.spack-env/view/bin/python"
uv sync --locked
uv run --locked depot --help
datalad --version
git annex version
quarto --version
```

If direnv already performs activation and exports `UV_PYTHON`, those settings do
not need to be repeated. Keep `-p`/`--prompt` out of Spack activation in `.envrc`;
see [prompt recovery](#troubleshooting). Spack owns the interpreter and uv owns
its project packages; see [environment details](#environment-details) for checks.

### Select one installation configuration

For an existing installation, reuse its reviewed configuration. For a new one,
use [examples/depot.toml](examples/depot.toml) as a starting point and edit all
roots before publishing. The following layout assumes `depot.toml` is in the
checkout and Prospectors are in its sibling `../prospectors` directory:

```toml
schema_version = 1
registry = "registry"
website = "notebooks"
source_roots = ["../prospectors"]
state = "state"
staging = "staging"
workspace = "workspace"

[targets.prospects]
layer = "02_prospects"
path = "/path/to/approved/goldmine/02_prospects"
access = "unlocked" # Default: populated ordinary files alongside the RIA archive.

[targets.refined]
layer = "03_refined"
path = "/path/to/approved/goldmine/03_refined"
```

Replace the target placeholders with reviewed, writable publication destinations.
All relative configuration paths resolve from the configuration file's directory.
Keep source, state, staging, workspace, publication targets, and website roots
mutually disjoint: none may contain another. `website = "notebooks"` points to
the shared Quarto source directory, with operational roots such as `state/` and
`staging/` as siblings. Setting `website` to the whole checkout would overlap
those operational directories and is rejected.

Keep this configuration private and outside the rendered website. This checkout
uses a gitignored `depot.toml`. Select it explicitly for the whole walkthrough:

```sh
export DEPOT_CONFIG="$PWD/depot.toml"
```

For another configuration location, adjust its relative paths or use an absolute
`website` path pointing to this checkout's `notebooks/` directory.
`--config FILE` overrides `DEPOT_CONFIG`; without either, Depot uses `depot.toml`.
The selected configuration determines the registry, fetched state, and storage
used by every command. A fetch under a demo configuration does not fetch data
under your real configuration.

### Use the shared catalogue and Manual website

The repository already contains the complete Quarto project in
`notebooks/_quarto.yml`. Keep `website = "notebooks"`; no second project or
website configuration is needed. The shared Manual format and authoring/emit
profiles render the site to **`docs/`**, the GitHub Pages output location.

`catalog build` owns `notebooks/index.qmd` and generated `notebooks/datasets/`
pages. The landing page is the lab-facing catalogue, with dataset descriptions,
versions, resource tables, and retrieval instructions. Authored operating
instructions live in `notebooks/overview.qmd` and the supporting Manual pages.

Quarto website navigation includes the generated dataset pages without a fixed
book chapter list. The navbar links the catalogue and Operator Manual, and site
search covers both. Rendering reads the public catalogue snapshot and Manual
sources; it does not open raw releases, fetch data, or publish to Goldmine.

For an existing installation previously using `website = "website"`, change
only that setting to `"notebooks"`, then rebuild the catalogue and render. Keep
the state, staging, workspace, and publication targets unchanged: verified
receipts remain valid and existing data does not need to be published again.
Preserve a previous standalone website in an archive outside `notebooks/` and
`docs/` while reviewing the migration.

<a id="add-data"></a>

## 3. Add a dataset and publish it end to end

This walkthrough uses **`kiribati-biomarkers`, version `v0.2.2`**. Substitute your
own dataset ID, release version, and Prospector paths when adding other data.
Keep the same `DEPOT_CONFIG` throughout. Run each step only after the previous
one succeeds.

### Confirm the Prospector has produced a release

The source must already contain a finished release such as:

```text
prospectorKiribatiBioMarkers/data/outputs/releases/
└── v0.2.2/
    ├── datapackage.json
    └── ... every local resource declared in datapackage.json
```

The Prospector must expose the complete version directory atomically and leave
its contents immutable. Depot does not execute the Prospector. Changed data
requires a new release version.

### Register the dataset

Create one reviewed `ID.yaml` in the `registry` directory selected by the
configuration. If it already exists, reuse it. For this walkthrough, the file
is `registry/kiribati-biomarkers.yaml`; a corresponding entry is:

```yaml
schema_version: 1
id: kiribati-biomarkers
title: Kiribati Biomarkers
description: Biomarker and Demographic Data for Kiribati
source:
  prospector: prospectorKiribatiBioMarkers
  releases: ../../prospectors/prospectorKiribatiBioMarkers/data/outputs/releases
destination:
  layer: 02_prospects
  target: prospects
versions:
  pattern: 'v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)'
policy:
  mode: automatic
checks:
  required_fields: [name, title, description]
  nonempty: true
  minimum_rows: 1
catalogue:
  visible: true
  audience: Lab members and authorized collaborators only.
```

The filename must match `id`. `source.releases` points to the directory
**containing version directories**, rather than to `v0.2.2` itself. Relative
source paths resolve from the **registry directory**; the example assumes the
layout in setup. Absolute source paths also work. The resolved source must lie
under a configured `source_roots` entry. `destination.target` names a configured
target, and its layer must match. Review metadata and audience before publication.
`catalogue.visible: true` makes a successfully published dataset eligible for display.

The `minimum_rows` check applies to every resource, including audit tables; allow
zero rows only if that is the reviewed policy. For Refined destinations, also
supply `policy.approved_dates` with allowed UTC publication dates. The
[registry schema](src/depot/schemas/registry-v1.schema.json) defines accepted fields.

### Fetch, validate, and publish the selected release

**Fetch is required before validation.** Run these commands in order:

```sh
uv run --locked depot --config "$DEPOT_CONFIG" fetch kiribati-biomarkers v0.2.2
uv run --locked depot --config "$DEPOT_CONFIG" validate kiribati-biomarkers v0.2.2
uv run --locked depot --config "$DEPOT_CONFIG" push kiribati-biomarkers v0.2.2
```

| Command | What happens | Expected status |
|---|---|---|
| `fetch` | Fingerprints the source, copies it into staging, verifies the copy, and records the candidate | `fetched` |
| `validate` | Checks that fetched candidate and records validation under the selected policy and destination | `validated` |
| `push` | Saves and publishes through DataLad, then clones, retrieves, fingerprints, and validates the published release | `success` |

`push` writes to the configured publication destination. Its `success` receipt
means fresh retrieval passed. Registration or validation alone does not create a
catalogue entry. A repeat push of an already verified publication can report
`unchanged`. It still checks and, if missing, recreates the ordinary-file view.

If validation says **"Fetch this release before validating or pushing it"**,
run the `fetch` command above with the same configuration, ID, and version, then
retry validation. The error means that selected configuration has no fetched
candidate or its staged directory is missing; the source release may still exist.

Inspect the internal attempt history when a step fails:

```sh
uv run --locked depot --config "$DEPOT_CONFIG" receipts kiribati-biomarkers
```

### Use the published files without DataLad

By default, `push` also creates populated, ordinary writable files at:

```text
GOLDMINE/02_prospects/kiribati-biomarkers.data/releases/v0.2.2/
```

Lab members can open these files directly in Python, R, or other tools. The
existing `GOLDMINE/02_prospects/kiribati-biomarkers/` remains the RIA archive;
its clone URL and history are preserved. The `.data` view is an independent
copy of the verified bytes, with no annex symlinks or placeholder files. It costs
an additional full copy on disk. Changes to that copy do not change the archive.
Copy shared data into a personal analysis directory before editing it.

The target setting `access = "unlocked"` is the default even when omitted. To
publish only the locked DataLad archive, set `access = "locked"` in the target's
TOML table. A dataset can override its target default in registry YAML:

```yaml
destination:
  layer: 02_prospects
  target: prospects
  access: locked # Optional; omit for the target's default.
```

Locked mode leaves retrieval to `datalad clone` and `datalad get`; it does not
create an ordinary-file view. It never deletes or locks a view created earlier.
Changing this access setting does not invalidate scientific validation.

For an already published release, repeat the **`push` command** to create its
new default view without changing the archived release commit or repeating
Frictionless validation. The fetched candidate and unchanged source must still
be available. Rebuild the catalogue afterward so its dataset page advertises
direct access. Existing views are fingerprinted: Depot refuses to overwrite
user edits. Preserve those edits, then restore or relocate the modified view
before retrying. The archived version remains available throughout.

### Build and render the data catalogue

After `push` succeeds:

```sh
uv run --locked depot --config "$DEPOT_CONFIG" catalog build
scripts/render-isolated --profile authoring
```

Expect `catalogued` for `kiribati-biomarkers`. Depot writes `notebooks/index.qmd`
and `notebooks/datasets/kiribati-biomarkers.qmd`. The render produces the whole
site in `docs/`: open **`docs/index.html`** to browse the catalogue and follow
the Kiribati entry to its metadata, resources, version, commit, and retrieval
commands. The navbar's **Operator Manual** link opens `docs/overview.html`.
The workflow is complete when the verified release appears on that landing page.
Publishing or deploying the website to a web host is a separate operation.

If the catalogue is empty, check for a `success` receipt with `verified: true`,
`catalogue.visible: true`, and a matching configured destination. Rebuilding and
rendering the catalogue can be repeated without publishing data again.

### Add another dataset or a later version

For another dataset, create its release and a new registry YAML, then repeat
`fetch → validate → push → catalog build → render` with its ID and version. For
a later version of an existing dataset, reuse its registry entry and fetch the
new version. The catalogue lists the greatest verified version in natural order
(`v2` before `v10`); version selection is not a full SemVer implementation.

After the selected-release workflow works, this command automates fetch,
validation, publication, retrieval verification, and catalogue generation:

```sh
uv run --locked depot --config "$DEPOT_CONFIG" sync
scripts/render-isolated --profile authoring
```

**`sync` visits every dataset and release directory in the selected registry.**
It has no dataset selector. Use the individual commands while testing Kiribati
alongside a long-running Madagascar validation. Sync isolates failures and builds
catalogue source even when a release fails; its nonzero exit status still needs
attention. An absent or empty source releases directory reports `no_new_release`.

<a id="troubleshooting"></a>

## Troubleshooting the walkthrough

| Symptom | Meaning and next step |
|---|---|
| `Fetch this release before validating or pushing it` | The selected configuration has no fetched candidate or staging is missing. Run `fetch ID VERSION` with that same `--config`, then `validate`. |
| `not_validated` when pushing | Run `validate ID VERSION` after fetch. Changes to registry policy or the destination require validation again. |
| `version_conflict` | Bytes or source identity changed under an immutable version. Inspect the release; corrected data needs a new version. |
| `dataset_locked` | Another operation owns this dataset's lock. Wait for it to finish; a different dataset can be processed independently. |
| `release_window_closed` | The UTC publication date is outside the registry's approved dates. Use the reviewed publication window. |
| Empty catalogue | Registration and successful validation are insufficient. Confirm verified publication, visibility, the destination, and the configuration used by `catalog build`. |
| `zsh: correct 'depot' to '.depot'?` | Decline the correction (`n`). `depot` is the installed command; `.depot` is a local scratch directory. This shell question is separate from Depot's reported error. |

If a demo path is still selected, reset `DEPOT_CONFIG` to your real installation
configuration before retrying the real-data commands. Receipts belong to that
configuration's `state` directory; retain them as publication evidence.

If Spack activation erased your SSH/Zsh prompt, ensure `.envrc` activates without
`-p`/`--prompt`, then run `direnv allow`. Direnv's child Bash can otherwise export
Spack's saved "no prompt" marker into Zsh, and a later activation unsets `PS1`.
For an already-affected terminal:

```zsh
unset SPACK_OLD_PS1
exec zsh -l
```

## Validation and recovery

Commands show the active phase and elapsed time with Rich. Validation runs resources
in parallel by default, using Frictionless's process pool. Set `PYTHON_CPU_COUNT`
before launching Depot to limit workers; Slurm examples use the allocated CPU count.
Each worker needs memory for a decoded table and pandas representation. Packages
with foreign keys run sequentially; library callers can also pass `parallel=False`
to `validate_package`. Parallel validation reports the phase and elapsed time;
sequential validation also identifies resources and reports rows every 10,000 rows.
Fingerprinting reports file counts. Batch jobs and redirected commands write
status lines to stderr, with repeated counts throttled to every 30 seconds.
Use `--json` for JSON results without progress messages. Ctrl-C exits with status 130.

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

<a id="synthetic-demo"></a>

## Optional: exercise the pipeline with synthetic data

This is a separate test installation. It is not a prerequisite for adding real
data. Run from the Depot checkout after software setup and choose a new, empty
scratch directory outside the checkout:

```sh
export DEPOT_DEMO=/tmp/depot-example
uv run --locked python scripts/demo.py "$DEPOT_DEMO"
git -C "$DEPOT_DEMO" init
uv run --locked depot --config "$DEPOT_DEMO/depot.toml" fetch example v1
uv run --locked depot --config "$DEPOT_DEMO/depot.toml" validate example v1
uv run --locked depot --config "$DEPOT_DEMO/depot.toml" push example v1
uv run --locked depot --config "$DEPOT_DEMO/depot.toml" catalog build
"$DEPOT_DEMO/scripts/render-isolated" --profile authoring
```

The helper creates a synthetic release and configuration, copies the shared
site/Manual source and render helper, and resets the catalogue snapshot to the
synthetic registry. The demo has the same single-site layout as the real project. Initializing its scratch Git root prevents DataLad from
discovering an unrelated ancestor repository under `/tmp` in this environment.
Expect `fetched`, `validated`, `success`, and `catalogued`, then inspect
`$DEPOT_DEMO/docs/index.html`. Every command names the demo configuration
explicitly, so your real `DEPOT_CONFIG` remains selected for real data.

## Retrieve published data

Depot uses one local RIA store per dataset beneath the configured target root.
It creates no parent Goldmine dataset or registered subdatasets. The publisher's
`goldmine` sibling depends on `goldmine-storage`, which transfers annexed bytes.
Verification explicitly retrieves from that storage sibling, excluding
publisher-local content as a source.

For a published Kiribati release, supply its actual RIA store and a new clone
location:

```sh
export DEPOT_STORE=/path/to/approved/goldmine/02_prospects/kiribati-biomarkers
datalad clone "ria+file://${DEPOT_STORE}#~kiribati-biomarkers" /path/to/new/kiribati-clone
cd /path/to/new/kiribati-clone
git checkout --detach COMMIT_FROM_SUCCESS_RECEIPT
datalad get --source goldmine-storage releases/v0.2.2
cat releases/v0.2.2/datapackage.json
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

<a id="environment-details"></a>

## Environment details

Verify that uv is using the Spack interpreter:

```sh
uv python find "$UV_PYTHON"
uv run --locked python -c 'import sys; print(sys.executable); print(sys.base_prefix)'
```

`sys.executable` should point into `.venv`; `sys.base_prefix` should point into
Spack's Python installation. Project uv settings disable uv-managed interpreters
and Python downloads. uv calls a Spack-installed interpreter a "system" Python;
this does not mean the operating system's Python. See
[uv's interpreter selection documentation](https://docs.astral.sh/uv/concepts/python-versions/).

`spack.yaml` and `spack.lock` describe the interpreter and Spack packages;
`uv.lock` records Python packages. After a Spack Python update, rerun
`uv sync --locked` with `UV_PYTHON` pointing to the current view. DataLad and
git-annex remain external CLI dependencies. The package uses Flit for builds.

## Manual source and website

All Manual pages, Quarto configuration, profiles, extensions, and project caches
live under `notebooks/`, matching the Madagascar Healthshed Clinic Data Manual.
The unified website uses `GoldenPlanetaryHealthLab/quarto-manual-html`. Its procedure blocks
emit the Python library into `src/depot` and the isolated render helper into
`scripts/render-isolated`; vendoring and the portable provenance changes are
recorded in
`notebooks/_extensions/GoldenPlanetaryHealthLab/quarto-emit/PROVENANCE.md`.

```text
notebooks/                  # Manual pages and all Quarto project files
  _quarto.yml               # One website with catalogue + Manual navigation
  _quarto-authoring.yml     # Default documentation profile
  _quarto-emit.yml          # Explicit generation profile
  _environment-*            # Profile emission settings
  _extensions/              # Shared Quarto Manuals extensions
src/depot/                  # Emitted Python library
scripts/render-isolated     # Emitted render helper
docs/                       # Unified GitHub Pages output; index.html is catalogue
```

Edit procedure code blocks in the Manual, then render or explicitly emit:

```sh
scripts/render-isolated --profile authoring
scripts/render-isolated --profile emit
uv run --locked pytest -q tests/test_emission.py
git diff
```

The default `authoring` profile renders the catalogue and Manual together into
`docs/` without changing Python source. The `emit` profile also synchronizes reviewed generated files.
Both use `engine: markdown` with computation disabled. The helper stages only
Manual and software sources, renders in isolation, and promotes results after a
successful render. It never copies released data or operational state. A test
checks exact agreement between Manual blocks and emitted source.

For direct Quarto use, run `env -u QUARTO_EMIT quarto render notebooks --profile authoring`
or `env -u QUARTO_EMIT quarto render notebooks --profile emit`. Clearing the inherited
flag lets the selected profile control emission; the helper does this automatically.
The isolated helper is the normal entry point on shared storage. See the
[rendering procedure](notebooks/rendering.qmd) for its source and boundaries.

The [catalogue walkthrough](notebooks/catalogue.qmd) reads reviewed registry
metadata and verified receipts into a pandas DataFrame. Great Tables builds the
catalogue, dataset metadata, and resource tables directly from DataFrames;
Python adds the minimal Quarto page text and retrieval commands. To inspect
the same data interactively, use
`catalogue_data(config)` and `catalogue_table(entries)` from `depot.catalog`.
Adding a dataset requires registry data and a verified release, with no Python
entry list to edit.

The generator writes `index.qmd` and `datasets/ID.qmd`. It excludes operational
paths/errors, hidden datasets, and failed releases. It removes only previously
tracked generated pages when visibility changes. Catalogue output goes to the
shared `docs/` output directory alongside the Manual. Deployment is a separate action.

## Tests

```sh
uv run --locked pytest -q --basetemp=.depot/readme-tests
uv run --locked ruff check src tests scripts
uv run --locked ruff format --check src tests scripts
scripts/render-isolated --profile authoring
```

Unit tests cover registry contracts, resource validation, path safety, content
conflicts, policy changes, schedules, receipts, catalogue privacy, idempotency,
locks, and failure isolation. Integration tests use synthetic data and temporary
local RIA stores, including fresh retrieval, failed push/retrieval recovery,
and preserving the prior catalogue after rejection. A separate integration check
renders both Manual profiles with a deliberate source change to verify that
default authoring does not emit and explicit emission does.

Publication tests skip clearly when DataLad, git-annex, or Git is missing;
the Manual profile check requires Quarto and rsync. A skip does not verify the
corresponding behavior. `pytest -m 'not integration'` runs unit tests only.
See `VALIDATION.md` for observed results and environment-specific limitations.

## Proposed FASRC scheduling — inactive

`scripts/sync.sbatch.example` is a proposed manual batch entry point. Set project
and configuration paths, review resources and tool activation, and test manually
before scheduling. It activates Spack, selects that environment's Python, and
runs Depot through `uv run --locked`; adjust the Spack initialization path for
your site. It renders catalogue updates even if one dataset fails,
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
The scheduling examples are not installed automatically. Review configured
publication destinations and shared-storage access before enabling recurring work.
