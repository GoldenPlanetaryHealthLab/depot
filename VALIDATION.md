# Implementation validation

Dated checks below distinguish synthetic integration tests from authorized
checks of real releases. Initial environment verification was on 2026-11-12.

## Environment

- Spack-managed Python 3.14.3
- DataLad 1.4.1
- git-annex 10.20250721-g8867e7590a3a70afa8a93d2fefab94adc9a176d0
- Quarto 1.9.38
- Frictionless 5.21.0
- Great Tables 0.24.0; pandas 3.1.1
- pytest 9.2.0; Ruff 0.17.5

Installed application/development dependencies match their versions in
`uv.lock`. Platform-specific packages, such as Windows-only dependencies, are
not installed on this Linux host. A Flit wheel build includes the registry
schema and CLI entry point.

## Completed checks

- Default populated, unlocked access (2026-11-14): retained each RIA archive
  at `TARGET_ROOT/ID` and added an independent ordinary-file view at
  `TARGET_ROOT/ID.data/releases/VERSION`. Target `access` defaults to `unlocked`;
  registry `destination.access` can override it. `locked` retains archive-only
  publication and never deletes an existing view. New managed annex files use
  `annex.addunlocked` according to that policy. Access changes preserve content
  validation bindings, and repeat pushes can materialize older verified releases
  without changing their archived commit or repeating Frictionless validation.
  The first publication records success only after materialization succeeds.
  Atomic copy, independent writable files, target/dataset overrides, redirected
  paths, missing-view recreation, and refusal to overwrite user edits are tested.
  `PYTHON_CPU_COUNT=2 .venv/bin/python -m pytest -q --basetemp=.depot/access-full-tests`:
  **72 passed**. Two subsequent integration checks in
  `.depot/access-recovery-tests` passed, including the newly added population
  failure/retry case and strengthened default-unlocked assertions: **73 distinct
  tests verified**, with nine distinct Quarto/DataLad integration cases overall.
  Explicit emit and authoring renders passed; source/manual consistency, Ruff
  lint, formatting of changed modules/tests, schema/example checks, shell syntax,
  and `git diff --check` passed.
  After the user selected the additive layout and the Goldmine write was
  authorized, repeated the real Kiribati `v0.2.2` push. Its new view contains
  `biomarker_ptx.csv` and `datapackage.json` as ordinary owner-writable files.
  Its fingerprint matches the successful receipt, and pandas read five rows
  and 25 columns directly. The archived commit remains
  `428bb3ae8faecd3f05ab6fab027b06ff34231834`. No Frictionless pass or archive push
  was repeated. Rebuilt the unified catalogue and rendered direct-access
  instructions without publishing private storage roots. No MDG release was
  validated or published by this change.
- Unified catalogue and Manual (2026-11-14): `notebooks/_quarto.yml` is now one
  website using the shared Manual format and authoring/emit profiles, rendering
  all pages to `docs/`. `catalog build` owns the lab-facing `notebooks/index.qmd`
  and generated dataset pages; operating instructions moved to `overview.qmd`.
  Native website navigation and search include both datasets and Manual pages
  without a fixed book chapter list. The local configuration and example now
  use `website = "notebooks"`. A local catalogue rebuild included the already
  verified `kiribati-biomarkers` `v0.2.2` without republishing; its validation
  binding remained unchanged. All rendered internal links and anchors passed,
  search included the dataset and Manual, and the public catalogue/detail pages
  contained no private filesystem roots or operational identity/fingerprint fields.
  The previous standalone website was preserved at
  `.depot/retired-website-ywp7kr3e/website`.
  `PYTHON_CPU_COUNT=2 .venv/bin/python -m pytest -q --basetemp=.depot/unified-final-tests`:
  **65 passed**, including all seven Quarto/DataLad integration tests. New coverage
  checks populated and empty unified sites, search/navigation, preservation of
  authored Manual/configuration files, and removal of stale dataset HTML.
  Executed the updated README's synthetic commands in
  `/tmp/depot-unified-demo-bsuh6w2n`: fetch, parallel validation, publication,
  fresh retrieval, catalogue generation, and the single site render all passed.
  The demo retained only synthetic catalogue entries and included its Operator
  Manual under the same `docs/` output. Ruff lint, formatting of changed Python
  files, shell syntax, and `git diff --check` passed.
- Quarto Manuals layout and direct tables (2026-11-13): moved Manual pages,
  book configuration, authoring/emit profiles, extensions, and caches under
  `notebooks/`, using the same Manual format as the Madagascar reference.
  `scripts/render-isolated --profile authoring` and `--profile emit` rendered
  all nine pages, whose internal page links and anchors passed inspection.
  Authoring preserved generated file hashes; emission synchronized the Python
  catalogue module. Removed standalone catalogue templates and `StringTemplate`;
  index, metadata, and resource tables now come directly from pandas/Great Tables.
  Rendered the synthetic catalogue and verified its three table types and pinned
  retrieval instructions. A separate rendered fixture preserved potentially
  active markup as literal metadata text.
  `PYTHON_CPU_COUNT=2 .venv/bin/python -m pytest -q --basetemp=.depot/manual-layout-tests`:
  **62 passed**, including all four DataLad integration tests. Subsequently added
  a profile regression test and ran
  `.venv/bin/python -m pytest -q tests/test_emission.py --basetemp=.depot/manual-profile-tests`:
  **2 passed**. That test makes a deliberate Manual-only change and inherits
  `QUARTO_EMIT=1`; default authoring must leave Python untouched and explicit emit
  must propagate the change. Quarto's profile environment files do not override
  inherited variables, so the helper clears that flag before loading a profile.
  The offline wheel build passed; importing from the wheel rendered a Great Table
  without template or `.qmd` package resources. A final rendered-table regression
  exposed Markdown interpretation inside unfenced table HTML; Great Tables output
  now uses Quarto raw-HTML blocks so cell values remain literal. The expanded suite
  at `.depot/manual-final-tests` passed 63 cases; the new rendering fixture failed
  because Quarto skipped inputs beneath the hidden `.depot` ancestor. After making
  the fixture render an isolated non-hidden temporary copy, its targeted run passed.
  The final `pytest --last-failed --basetemp=.depot/manual-final-rerun` run passed
  that remaining case, verifying all 64 distinct tests across the suite and rerun.
  The final wheel was rebuilt and checked for raw-table handling. Ruff lint, formatting of the
  changed Python files, shell syntax, and `git diff --check` passed. The broader
  formatting check still identifies existing formatting in unchanged `cli.py`,
  `publication.py`, and `service.py`; this reorganization did not reformat them.
- Operator walkthrough reorganization (2026-11-13): checked the README's embedded
  TOML, Quarto YAML, registry schema/version expression, resolved Kiribati source
  path, and shell syntax. Ran the optional demo commands extracted from the README
  against `/tmp/depot-readme-demo-mklot66p`, with a separate scratch Git root and
  two validation workers. Observed `fetched`, `validated`, `success`, and
  `catalogued`; verified the fresh-retrieval receipt, rendered catalogue entry,
  dataset detail page, and retrieval instructions. Rendered all eight operator
  documentation pages in `/tmp/depot-readme-render-pc03m2qy` and checked their
  internal page links and anchors. The source/manual consistency test and
  `git diff --check` passed. Real Kiribati inspection was read-only: the release
  and its one-resource package existed, while the selected configuration had no
  fetched candidate for `v0.2.2`. No real release was fetched or published.
- SSH/Zsh prompt preservation (2026-11-13): reproduced in isolated `zsh -f`
  with a known `PS1`, actual `eval "$(direnv export zsh)"`, then manual
  `spack env activate -d "$PWD"`. The original `.envrc` used `-p`, exporting
  `SPACK_OLD_PS1='$$$$'` from direnv's child Bash. Direnv preserved Zsh's `PS1`,
  but manual activation restored that saved absent prompt by unsetting `PS1`.
  Removed `-p` from the gitignored local `.envrc` and re-authorized it with
  `direnv allow .`. The same diagnostic then preserved the exact prompt through
  direnv loading, two manual activations, and deactivation; no saved-prompt
  variable leaked from the child shell. Spack environment activation was also
  asserted, so an unloaded `.envrc` could not give a false pass. Shell syntax
  and `git diff --check` passed. The versioned README records the activation
  convention and recovery for existing terminals.
- Parallel validation default (2026-11-13):
  `PYTHON_CPU_COUNT=2 .venv/bin/python -m pytest -q --basetemp=.depot/parallel-validation-tests`:
  **62 passed**, including all four real DataLad publication/retrieval tests; no skips.
  Real worker processes checked equivalent CSV and Parquet results in parallel and
  sequential modes, preserved schema/minimum-row failures, and retained foreign-key
  enforcement through sequential fallback. The notebook rendered and emitted
  `validation.py` in an isolated temporary project; source/manual consistency,
  targeted Ruff lint/format, shell syntax, and `git diff --check` passed.
  As described below, the initial full-suite run under `/tmp` passed 58 tests but
  failed the four publication tests on unrelated Git ancestor ownership checks;
  repository-local temporary data resolved that test-environment issue.
- Spack/uv interpreter ownership: `uv sync --locked` completed with `UV_PYTHON`
  set to the Spack view's `bin/python`. `uv run --locked python` reported the
  project's `.venv` executable and a `sys.base_prefix` matching the installed
  Spack Python prefix (`python@3.14.3`, hash `rgmy5oy`).
  `uv run --locked pytest -m 'not integration' -q`: **45 passed**, four integration
  tests deselected. Shell syntax checks passed for `.envrc`, the development
  launcher, and the sync batch example. A dry-run sync with a missing selected
  interpreter failed rather than choosing another Python. The existing Spack
  installation was used without reconcretizing or installing Spack packages.
- Catalogue DataFrame/Great Tables refactor:
  `.venv/bin/python -m pytest -q --basetemp=.depot/catalogue-refactor-tests`:
  **49 passed**, including all four real DataLad integration tests; no skips.
  Added coverage for latest verified version selection, the empty DataFrame,
  literal metadata, public column projection, and deterministic detail pages.
- Emitted `catalog.py` using `QUARTO_EMIT=1 quarto render` in an isolated copy;
  the manual/source consistency test passed. Rendered all nine pages of a
  synthetic catalogue, including its dataset page, and checked table IDs,
  links, literal metadata, and the decoded commit-pinned retrieval commands.
  A separate eight-page render of the repository website also passed, and
  its output refreshed ignored `docs/`. Ruff lint/format and `git diff --check`
  passed for the refactor.
- `.venv/bin/python -m pytest -q --basetemp=.depot/final-tests`:
  **46 passed**, including all four real DataLad integration tests; no skips.
- After the final CLI progress-display change,
  `.venv/bin/python -m pytest -m 'not integration' -q`:
  **42 passed**, four integration tests deselected.
- Ruff lint and formatting: passed for `src`, `tests`, and `scripts`.
- `bash -n scripts/sync.sbatch.example` and `git diff --check`: passed.
- Final wheel: packaged schema, CLI entry point, and current emitted CLI checked.
- Manual `fetch`, `validate`, `push`, and repeat `sync`: successful Rich output;
  repeat publication reports `unchanged`.

## Publication evidence

The temporary local RIA experiment confirmed that the CSV was annexed, both
Git history and annex content were pushed, and a fresh clone retrieved the
original bytes. The implementation's integration tests explicitly select
`goldmine-storage` during retrieval, then compare the full release fingerprint
and rerun Frictionless validation.

The integration suite covers multiple valid versions with pinned commits,
duplicate avoidance, an invalid new release retaining the prior catalogue,
source mutation under an existing version, recovery from failed retrieval and
failed push, and two datasets where only one succeeds. These are local
publication checks, not shared Goldmine deployment evidence.

## Website and source emission

The synthetic dataset's two-page catalogue rendered successfully at
`/tmp/depot-demo-review/website/_site/index.html`. The full eight-page website
and operator manual rendered successfully at
`/tmp/depot-site-check/docs/index.html`.

The full site check used an isolated copy of `_quarto.yml`, `index.qmd`,
`notebooks/`, and `_extensions/`. Running
`QUARTO_EMIT=1 quarto render /tmp/depot-site-check` both emitted Python and
rendered the site. Emitted Python and rendered output were copied back to the
checkout. The manual/source consistency test checks every generated module
byte for byte. No analytical notebooks or ingestion commands execute during
rendering.

The local emitter patch strips absolute paths from generated header provenance.
One code block also avoids literal double-brace shell-variable syntax inside
Python f-strings because the emitter treats double braces as template variables.
The catalogue test checks the resulting shell reference remains correct.

## Environment-specific limitations

DataLad discovers an unrelated `.git` ancestor under `/tmp` in this execution
environment. Initial tests there failed on ancestor initialization/ownership.
The passing suite places temporary synthetic fixtures in the ignored
`.depot/final-tests` directory beneath the existing checkout, using pytest's
supported `--basetemp` option. The external demonstration used its own empty
scratch Git root to bound ancestor discovery. No global Git ownership exception
or DataLad environment override was added.

Direct Quarto rendering in the shared checkout emitted/rendered pages but
failed while removing `.quarto/_freeze`, reporting `Directory not empty` and
`Device or resource busy`. Moving the incomplete cache aside did not resolve
it. Another attempt encountered a missing `.agents` entry during resource
discovery. Rendering the same website in a clean temporary copy succeeded.
This narrows the failure to the checkout/runtime; the precise filesystem cause
has not been established. No website configuration workaround was added.

Shared-storage ACLs, group ownership, quotas, cross-user retrieval, compute-node
access, and shared-filesystem lock behavior remain unverified. No live Goldmine
target or recurring job was configured. The scheduling script and scrontab
entry are documentation only.
