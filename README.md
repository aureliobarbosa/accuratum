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
# By location string (resolved via Nominatim/OpenStreetMap). Creates the
# project folder belem-brazil_<year>_p0/ with project.json, polylines.npz and
# accuratum.png
accuratum "belem, brazil"

# By explicit latitude/longitude (use '=' for negative values)
accuratum --lat-long=-15.78,-47.92 --output brasilia.png

# The other half-year frame (June → December) of a given year
accuratum --lat-long=-15.78,-47.92 --year 2026 --period 1

# Override the overlay logo and its position/size (figure coords, 0-1)
accuratum --lat-long=0,0 --logo my_logo.png --logo-rect=0.1,0.8,0.15,0.15

# Vector output (.svg or .pdf) that a print shop can scale to any panel size
accuratum --lat-long=-15.78,-47.92 --output panel.svg

# Hand-edit labels in <folder>/project.json, then render without recomputing
accuratum --project lat-15.78_lon-47.92_2026_p0 --output clock.svg

# After editing the spec in project.json (e.g. "period"), recompute it
accuratum --project lat-15.78_lon-47.92_2026_p0 --regenerate
```

### Project folders

Each run saves a folder (`--project-dir` sets it; an existing one is only
overwritten with `--force`):

- `project.json` — short and hand-editable: the `spec` (location, year,
  period, grid, ...), the `render` settings (font size, logo and compass) and the `labels`, one per line. Move a label by editing `x`/`y`;
  hide or restore one with `hidden` (labels the placement heuristic suppressed
  are kept, hidden); add one by appending `{"text": "...", "x": 0, "y": 3}`.
- `polylines.npz` — the computed day and hour lines (NumPy arrays).

Rendering a folder with `--project` uses the saved lines and labels as they
are. Render flags given on the command line win over the saved settings for
that run. If the spec was edited, `--project` refuses and asks for
`--regenerate`, which recomputes lines and labels (label edits are lost; the
previous file is kept as `project.json.bak`).

Hour lines are labelled in the zone's **standard time**. Where daylight
saving applies, add one hour to the dial's reading in summer, as with any
sundial.

Latitudes from 75° S to 75° N are supported. Past about 56.5°, the winter
sun stays below the 10° horizon cut for some weeks around the solstice, so
the dial covers less of the year the closer it is to the poles.

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
from accuratum.renderers import matplotlib_backend

tz = ZoneInfo("America/Sao_Paulo")
spec = SundialSpec(
    location=Location(lat=-15.78, lon=-47.92, timezone="America/Sao_Paulo"),
    timeframe=TimeFrame(start=datetime(2025, 12, 21, tzinfo=tz), end=datetime(2026, 6, 21, tzinfo=tz)),
)
plot = build_plot(spec)  # pure data: polylines + labels, no matplotlib

fig, _ = matplotlib_backend.render(plot, RenderHints())
fig.savefig("clock.png", dpi=200, bbox_inches="tight")
fig.savefig("clock.svg", bbox_inches="tight")  # vector; .pdf works too
```

To save and reload a project folder from Python, use
`accuratum.core.project.Project` with `accuratum.core.project_io.save_project`
/ `load_project`.

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
