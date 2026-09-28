# **Accuratum**

### A Python library and CLI for creating *Accuratum sundials*

Accuratum draws a horizontal sundial (the shadow cast by a plumb/gnomon on a
flat surface) for a given location on Earth, computed precisely with
[astropy](https://www.astropy.org/) and [astroplan](https://astroplan.readthedocs.io/).
A full year is covered by two solstice-to-solstice frames
(December → June and June → December).

## Install

Accuratum is not (yet) published on PyPI. Install it directly from GitHub:

```bash
pip install git+https://github.com/aureliobarbosa/accuratum.git
```

Pin to a branch, tag, or commit if needed:

```bash
pip install git+https://github.com/aureliobarbosa/accuratum.git@main
pip install git+https://github.com/aureliobarbosa/accuratum.git@<tag-or-sha>
```

Requirements: Python ≥ 3.11. Major dependencies (astropy, astroplan, matplotlib,
geopy, numpy, timezonefinder) are installed automatically.

## CLI usage

After installation the `accuratum` command is available:

```bash
# By location string (resolved via Nominatim/OpenStreetMap)
accuratum "belem, brazil" --output belem.png

# By explicit latitude/longitude (use '=' for negative values)
accuratum --lat-long=-15.78,-47.92 --output brasilia.png

# Render the other half-year frame (June → December)
accuratum --lat-long=-15.78,-47.92 --period 1

# Override the overlay logo and its position/size (figure coords, 0-1)
accuratum --lat-long=0,0 --logo my_logo.png --logo-rect=0.1,0.8,0.15,0.15

# Vector output in real millimetres, e.g. a 6 m x 2 m panel (.pdf also works)
accuratum --lat-long=-15.78,-47.92 --canvas-size-mm=6000,2000 --output panel.svg

# Save the resolved spec as JSON, hand-edit it (e.g. label overrides), re-render
accuratum --lat-long=-15.78,-47.92 --save-spec clock.json
accuratum --spec clock.json --output clock.svg
```

See `accuratum --help` for the full list of options (grid resolution,
timezone override, plumb length, etc.).

Geocoding uses the free [Nominatim](https://nominatim.org/) service via
`geopy`, which has strict rate limits and requires network access. For
batch or reproducible use, prefer `--lat-long`.

## Library usage

A `SundialSpec` describes the sundial; `build_plot` turns it into a `Plot`
(pure data); a renderer draws it. Labels are plain data: each endpoint label
has its own `selector`, and labels the placement heuristic suppressed are kept
with `hidden=True`.

```python
from datetime import datetime
from zoneinfo import ZoneInfo

from accuratum.core.builder import build_plot
from accuratum.core.hints import RenderHints
from accuratum.core.spec import Location, SundialSpec, TimeFrame
from accuratum.renderers import matplotlib_backend, svg_backend

tz = ZoneInfo("America/Sao_Paulo")
spec = SundialSpec(
    location=Location(lat=-15.78, lon=-47.92, timezone="America/Sao_Paulo"),
    timeframe=TimeFrame(start=datetime(2025, 12, 21, tzinfo=tz), end=datetime(2026, 6, 21, tzinfo=tz)),
)
plot = build_plot(spec)  # pure data: polylines + labels, no matplotlib

fig, _ = matplotlib_backend.render(plot, RenderHints())
fig.savefig("clock.png", dpi=200, bbox_inches="tight")

with open("clock.svg", "w", encoding="utf-8") as fh:  # real millimetres, e.g. a 6 m x 2 m panel
    fh.write(svg_backend.render(plot, RenderHints(canvas_size_mm=(6000, 2000))))
```

The same spec can be saved and reloaded as JSON from the CLI:
`accuratum --lat-long=-15.78,-47.92 --save-spec clock.json`, then
`accuratum --spec clock.json -o clock.svg`.

## Development

Development uses [uv](https://docs.astral.sh/uv/) and runs inside a devcontainer.

```bash
git clone https://github.com/aureliobarbosa/accuratum.git
cd accuratum
uv sync --extra dev
uv run pytest
uv run accuratum --help
```

Code formatting/linting:

```bash
uv run ruff check --fix
uv run ruff format
```

Prototype notebooks live in [`notebooks/`](notebooks/) and are not shipped
in the built distribution.

## License

MIT — see [LICENSE.md](LICENSE.md).

## Authors

- Paulo Eduardo de Brito (creator)
- Marco Aurélio Alves Barbosa
