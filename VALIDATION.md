# Implementation validation

Observed on 2026-11-12 using synthetic data only.

## Environment

- Python 3.14.3
- DataLad 1.4.1
- git-annex 10.20250721-g8867e7590a3a70afa8a93d2fefab94adc9a176d0
- Quarto 1.9.38
- Frictionless 5.21.0
- pytest 9.2.0; Ruff 0.17.5

Installed application/development dependencies match their versions in
`uv.lock`. Platform-specific packages, such as Windows-only dependencies, are
not installed on this Linux host. A Flit wheel build includes the registry
schema and CLI entry point.

## Completed checks

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
