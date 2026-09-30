"""The landing page's carousel: one sundial per university campus.

Generated once, not per visit, and served as static files::

    cd web && uv run python -m accuratum_web.gallery

Each image shows the half-year in progress on the day it is generated and
is titled with its city. The logo is the project's own, except at UnB, which
keeps its university logo (the package default).
"""

import json
import re
import sys
import unicodedata
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

from timezonefinder import timezone_at

from accuratum.core.builder import build_plot
from accuratum.core.spec import SOLSTICE_DAY, GridConfig, Location, SundialSpec, solstice_timeframe
from accuratum.defaults.overlays import ACCURATUM_LOGO, DEFAULT_OVERLAYS, default_render_hints, resolve_image_path
from accuratum.renderers.matplotlib_backend import render

GALLERY_DIR = Path(__file__).parent / "static" / "gallery"
PNG_DPI = 120


@dataclass(frozen=True)
class University:
    name: str
    city: str
    lat: float
    lon: float


# Main campus coordinates, to about 0.01°.
UNIVERSITIES = (
    University("Universidade de Brasília", "Brasília", -15.7631, -47.8706),
    University("Universidad de Chile", "Santiago", -33.4446, -70.6507),
    University("Universidad Central de Venezuela", "Caracas", 10.4906, -66.8906),
    University("Universidad Nacional Autónoma de México", "Ciudad de México", 19.3322, -99.1870),
    University("Columbia University", "New York", 40.8075, -73.9626),
    University("University of Toronto", "Toronto", 43.6629, -79.3957),
    University("Universidade de Lisboa", "Lisboa", 38.7527, -9.1581),
    University("Sorbonne Université", "Paris", 48.8487, 2.3431),
    University("The University of Tokyo", "Tokyo", 35.7126, 139.7620),
    University("Peking University", "Beijing", 39.9869, 116.3059),
)


def half_year(today: date) -> tuple[int, int]:
    """The ``(year, period)`` whose solstice-to-solstice frame contains *today*."""
    june = date(today.year, 6, SOLSTICE_DAY)
    december = date(today.year, 12, SOLSTICE_DAY)
    if today < june:
        return today.year, 0
    if today < december:
        return today.year, 1
    return today.year + 1, 0


def title_for(uni: University) -> str:
    return uni.city


def logo_for(uni: University) -> str:
    return DEFAULT_OVERLAYS["logo"].image_path if uni.name == "Universidade de Brasília" else ACCURATUM_LOGO


def _slug(text: str) -> str:
    """``Ciudad de México`` → ``ciudad-de-mexico``: accents dropped, not the letters."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


def generate(
    out_dir: Path, today: date, grid: GridConfig = GridConfig(), universities=UNIVERSITIES
) -> list[dict[str, str]]:
    """Write one PNG per university and ``index.json``; return the index."""
    out_dir.mkdir(parents=True, exist_ok=True)
    year, period = half_year(today)
    entries = []
    for uni in universities:
        tz_name = timezone_at(lat=uni.lat, lng=uni.lon) or "UTC"
        spec = SundialSpec(
            location=Location(lat=uni.lat, lon=uni.lon, timezone=tz_name, name=title_for(uni)),
            timeframe=solstice_timeframe(year, period, ZoneInfo(tz_name)),
            grid=grid,
            year=year,
            period=period,
        )
        plot = build_plot(spec)  # its default title is the location name: the city
        hints = default_render_hints()
        overlays = [replace(o, image_path=logo_for(uni)) if o.name == "logo" else o for o in hints.overlays]
        hints = replace(hints, overlays=[replace(o, image_path=resolve_image_path(o.image_path)) for o in overlays])
        fig, _ = render(plot, hints)
        image = f"{_slug(uni.city)}.png"
        fig.savefig(out_dir / image, dpi=PNG_DPI, bbox_inches="tight")
        entries.append({"city": uni.city, "image": image, "subtitle": plot.subtitle})
        print(f"{uni.city}: {image}", file=sys.stderr)
    (out_dir / "index.json").write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return entries


if __name__ == "__main__":
    generate(GALLERY_DIR, date.today())
