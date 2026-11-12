Depot: first implementation handoff
Implement the first useful version of Depot, the lab's data catalogue and release publisher. Depot is a Python application with a small Quarto website (not a book). Its landing page contains a table of available datasets; each published dataset has a detail page. DataLad performs dataset versioning and publication through its command-line interface. Do not introduce DuckLake, a database service, a web server, or an elaborate orchestration framework.

The Frontier distinguishes a Prospector's output space from the Goldmine. Prospectors write immutable, version-named Frictionless Data Packages under:

data/outputs/releases/VERSION/datapackage.json

Depot reads registered releases, applies a standing manifest policy, and publishes accepted releases to a configured Goldmine destination such as 02_prospects or 03_refined. Prospects may receive frequent versioned releases for lab-wide use; refined releases have stricter schedules and acceptance criteria. Minted and external distribution are out of scope for this milestone. Never infer a trust tier from the package's directory name or successful file transfer. A rejected release must not change the last published version or its catalogue entry. An absent new release is a successful no-op.
First milestone
Using a fixture Prospector and a temporary local Goldmine destination, prove this exact round trip:
1. Register one dataset with a source releases directory, destination, and policy.
2. Fetch one version into a Depot-owned staging area without altering the Prospector's output.
3. Validate the registry entry and Frictionless Data Package, including referenced local resources.
4. Save the accepted version in a Depot-managed DataLad dataset and publish it to the configured destination.
5. From a fresh clone, retrieve the published data and verify the package and files.
6. Record a success receipt, generate the landing table and dataset detail page, and render the Quarto site.
7. Repeat the operation: it should be idempotent and not publish a duplicate.
8. Introduce a bad release: the command should report failure, retain the previous successful catalogue entry, and leave other registered datasets eligible for processing.
Build the manual commands and tests first. Do not install a scrontab entry or deploy a live Goldmine publication target during this milestone. Provide the future scheduled command in documentation only.
Repository shape
Use the existing repository if one is supplied; otherwise scaffold a new depot repository with approximately this shape. Adapt names to conventions already present without changing the separation of concerns.
depot/
  _quarto.yml                  # website configuration
  index.qmd                    # catalogue landing page
  datasets/                   # generated dataset detail pages; no private data
  registry/                   # reviewed, version-controlled publication policies
    example.yaml
  schemas/                    # JSON Schema for Depot registry/policy
  notebooks/                  # quarto manual for code description and src file emitting
  src/depot/                  # Python CLI and library
  tests/                      # fixtures and integration tests
  scripts/                    # optional thin batch-job entry point
  README.md
  pyproject.toml
Keep large datasets and transient intake work out of the website Git repository. Use configurable paths for a Depot-managed DataLad workspace, a staging area, and Goldmine publication targets. Never commit real data, credentials, cluster paths, or annex objects into a public website repository. Keep generated HTML derived from receipts and safe metadata, not from an uncontrolled directory scan.
Registry and validation
Provide one YAML manifest per dataset with an explicit, versioned schema. Suggested minimum fields: stable dataset ID, title, source releases path, destination layer and publication target, allowed version naming convention, release policy, required package fields/checks, and catalogue visibility. Distinguish public display metadata from internal operational paths. Do not put tokens in manifests or Git remote URLs.

There are two validation contracts:
- Depot validates the registry YAML against its own JSON Schema and checks that destination and version values are allow-listed; paths must remain inside the configured roots.
- Depot validates the Prospector's datapackage.json with the Frictionless Python library, verifies every declared local resource exists within the release, and applies the registry's additional checks. Reject traversal, symlink escape, incomplete files, missing metadata, invalid versions, or an unauthorized destination. Consult installed Frictionless APIs rather than guessing method names.
Treat a release version as immutable. Record its source identity and a reproducible content fingerprint; if the same version's contents later differ, reject it and flag the conflict. A stricter refined policy may specify approved release windows or extra checks, but do not make routine Prospects wait for a manual approval on every version.
CLI and DataLad mechanics
Implement a readable Python package and CLI using Quarto Manuals to emit Python script content. Use argparse (or another small parser) with Rich for status tables, progress, and actionable errors. Keep command behavior available as ordinary Python functions for tests. Initially expose:
depot fetch DATASET_ID VERSION
depot validate DATASET_ID VERSION
depot push DATASET_ID VERSION
depot catalog build
depot sync                         # loops over all registered candidates
fetch is a read-only import from the Prospector into Depot staging, not an instruction to run the Prospector or edit its release. validate reports structured failures and does not publish. push must refuse an unvalidated candidate, save its content via the DataLad CLI, publish both Git history and annexed file content to the correct configured sibling, and verify availability from a new clone/retrieval. catalog build renders only successfully verified versions. sync calls the same primitives for each registered dataset; catch and record a dataset's failure, continue with the others, and exit nonzero at the end if any failed. Use per-dataset locking to prevent overlapping runs.

Invoke DataLad through subprocess.run([...], check=True, ...) with argument arrays, never shell interpolation. Surface command failures without printing secrets. Select the simplest supported DataLad publication layout after proving it in a temporary local integration test. A DataLad push to a bare repository or RIA store does not imply a populated, ordinary working-tree folder at gold_mine/02_prospects/<id>. Document the actual clone/get path that a future Stagecoach client will use. If the desired Goldmine layout requires a parent DataLad dataset and registered subdatasets, demonstrate and test that separately rather than assuming a push performs it.

Use receipts for the publication boundary. Each attempt should record dataset ID, version, source fingerprint, validation result, DataLad commit, target, verification result, timestamp, and any error. Make the successful receipt only after the fresh retrieval check passes. DataLad publication and website rendering cannot be one atomic transaction; if the latter fails, rerunning should complete the catalogue without republishing the dataset. Never advertise a failed or partially published release as available. Preserve earlier success receipts and history.
Website
Use project: type: website. The landing page should show a simple table: dataset title/ID, layer, latest verified version, short description, last published date, and a link to its detail page. Each detail page should show provenance (Prospector name and release version), resource summary, validation/publication status, intended audience or use, and a reproducible staging/clone reference suitable for the lab. Link to package metadata where it is safe and reachable. Provide a brief note that Prospects can change and Refined releases follow a stricter schedule. Keep private paths and operational error details out of publicly published pages.

Generate the table and detail pages deterministically from the registry, package metadata, and successful receipts. Sorting and URLs must be stable. An internal command or log should show rejected releases without putting them in the public catalogue. Make the site render without retrieving large annexed files or executing analytical notebooks. Follow the repository's existing Quarto/GitHub Pages conventions if present.
Tests and handoff
Create small synthetic Frictionless fixtures. Unit-test registry validation, path safety, package validation, version conflicts, catalogue filtering, and per-dataset error handling. Integration-test the DataLad round trip in temporary directories with a local sibling, including a fresh clone and datalad get of annexed content. Skip integration tests clearly when DataLad/git-annex are unavailable; do not report a skipped test as a verified publication. Test one valid release, invalid package, source mutation under an existing version, repeat run, failed publication, and two datasets where one fails while the other succeeds.

Provide README.md with setup, a sample manifest, manual commands, expected output, the verified data retrieval procedure, and a proposed FASRC scrontab job script/entry without activating it. Explain prerequisites and any uncertainty about the configured shared storage and permissions. Finish by running available tests and a local Quarto render; report what passed and what could not be tested. Do not claim a production Goldmine deployment or live scheduled ingestion until those have been separately authorized and verified.

Avoid new abstractions until the one-dataset round trip succeeds. The governing principle is: the catalogue describes only versions Depot has actually validated and made retrievable.