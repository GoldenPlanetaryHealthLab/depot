# Quarto Manual extension provenance

Depot uses Quarto Manual v0.1.0, Quarto-emit v1.0.0, and Font Awesome v1.3.0,
matching the vendored copies in `prospectorMDGHealthshedClinicData` at commit
`46a0a37ed116713abebf9a0826ae15ea838bc495`. The Manual and Font Awesome directories
were copied without changes from that reference's `notebooks/_extensions`.

The emit filter was originally vendored from GoldenPlanetaryHealthLab/QuartoManual,
commit `1e2392aeda1b02e26419a045758020f7271952bb`:

- `_extensions/TinasheMTapera/quarto-emit/_extension.yml`
- `_extensions/TinasheMTapera/quarto-emit/quarto-emit.lua`

Upstream: https://github.com/GoldenPlanetaryHealthLab/QuartoManual

Depot keeps two small local changes to that emit filter:

1. Generated headers use the source Manual's basename rather than an absolute
   `quarto.doc.input_file`, keeping emitted Python reproducible across checkouts.
2. The emission manifest is stored in the Quarto project's `.quarto` directory,
   `notebooks/.quarto/quarto-emit-manifest.tsv`, so no root-level sidecar is created.

All extensions now live under `notebooks/_extensions/GoldenPlanetaryHealthLab`.
The shared Manual format applies the semantic Manual renderer and emit filter. Default
`authoring` rendering sets `QUARTO_EMIT=0`; explicit `emit` rendering sets it to 1.
Both disable computation. The isolated render helper promotes generated Python
and the helper script only after successful rendering.

Upstream's check mode logs differences rather than failing the process, so
`tests/test_emission.py` also compares generated files with their Manual blocks.
