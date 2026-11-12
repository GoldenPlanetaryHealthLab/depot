Vendored from GoldenPlanetaryHealthLab/QuartoManual,
commit `1e2392aeda1b02e26419a045758020f7271952bb`, files:

- `_extensions/TinasheMTapera/quarto-emit/_extension.yml`
- `_extensions/TinasheMTapera/quarto-emit/quarto-emit.lua`

Upstream: https://github.com/GoldenPlanetaryHealthLab/QuartoManual

Local change: generated header provenance uses the manual's basename instead
of `quarto.doc.input_file`, which Quarto 1.9 supplies as an absolute path. This
keeps generated Python reproducible across checkouts and avoids committing
private cluster paths. The emission behavior is otherwise unchanged.

Only the emission extension is used. Depot remains a Quarto website and does
not adopt the template's book configuration. Emission requires `QUARTO_EMIT=1`;
ordinary renders only display manual content. Upstream's check mode logs
differences but does not fail a process, so `tests/test_emission.py` also compares
the checked-in Python source with the manual's code blocks.
