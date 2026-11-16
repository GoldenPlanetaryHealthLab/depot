# Manual extensions

This directory vendors the same reviewed extensions as
`prospectorMDGHealthshedClinicData` at commit
`46a0a37ed116713abebf9a0826ae15ea838bc495`:

- Quarto Manual v0.1.0;
- Quarto-emit v1.0.0;
- Font Awesome v1.3.0, used by the Manual's semantic callouts.

The default `authoring` profile renders the shared site with computation and emission
disabled. The explicit `emit` profile sets `QUARTO_EMIT=1` and also writes reviewed
Python sources and the render helper. Both use
`GoldenPlanetaryHealthLab/quarto-manual-html`.

The emit extension retains Depot's portable source-basename provenance and keeps
its audit manifest under `notebooks/.quarto/`; see
[provenance](GoldenPlanetaryHealthLab/quarto-emit/PROVENANCE.md).
