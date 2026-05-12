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
```

See `accuratum --help` for the full list of options (grid resolution,
timezone override, plumb length, etc.).

Geocoding uses the free [Nominatim](https://nominatim.org/) service via
`geopy`, which has strict rate limits and requires network access. For
batch or reproducible use, prefer `--lat-long`.

## Library usage

```python
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from accuratum.astronomy import compute_blocks, dayline_grid, hourline_grid
from accuratum.datetime_utils import frame_periods, get_solstices
from accuratum.graph import plot_solar_clock

lat, lon = -15.78, -47.92
now = datetime.now(tz=ZoneInfo("America/Sao_Paulo"))
period = frame_periods(get_solstices(now))[0]

daylines = dayline_grid(period, lat=lat, lon=lon,
                        day_step=timedelta(days=7), line_points=500)
hourlines = hourline_grid(period, lat=lat, lon=lon,
                          day_step=timedelta(days=1),
                          time_step=timedelta(minutes=20))

xs, ys = compute_blocks(daylines_grid=daylines, hourlines_grid=hourlines,
                        lat=lat, lon=lon, plumb_length=1.0)

fig, _ = plot_solar_clock(xs, ys, plumb_xy=(0, 0))
fig.savefig("clock.png", dpi=200, bbox_inches="tight")
```

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
