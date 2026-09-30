"""One website request → both half-year sundials as two PNGs and a two-page PDF.

This is the trust boundary: everything here comes from a visitor. The grid
is fixed (the spec bounds stop absurd values, not slow ones), colors are
``#rrggbb`` only, texts are capped and can't trigger matplotlib's mathtext,
and uploaded images are decoded and re-encoded before matplotlib reads them.
"""

import io
import re
import tempfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field, replace
from pathlib import Path
from zoneinfo import ZoneInfo

from matplotlib.backends.backend_pdf import PdfPages
from PIL import Image, UnidentifiedImageError
from timezonefinder import timezone_at

from accuratum.core.builder import build_plot
from accuratum.core.hints import RenderHints
from accuratum.core.plot import Plot
from accuratum.core.spec import GridConfig, Location, SundialSpec, solstice_timeframe
from accuratum.defaults.overlays import default_render_hints, resolve_image_path
from accuratum.renderers.matplotlib_backend import render

GRID = GridConfig()  # the CLI's defaults: about 10 s per half-year
PERIODS = (0, 1)  # Dec→Jun, Jun→Dec
MAX_TEXT_LENGTH = 80
MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_IMAGE_SIDE = 2000
PNG_DPI = 150
COLOR = re.compile(r"#[0-9a-fA-F]{6}")


@dataclass(frozen=True)
class PageTexts:
    title: str
    subtitle: str


@dataclass(frozen=True)
class SundialRequest:
    """What the visitor sends. ``logo``/``compass`` are raw uploads; ``None`` keeps the default."""

    lat: float
    lon: float
    year: int
    dayline_color: str
    hourline_color: str
    pages: tuple[PageTexts, ...]
    logo: bytes | None = None
    compass: bytes | None = None

    def __post_init__(self) -> None:
        for name in ("dayline_color", "hourline_color"):
            value = getattr(self, name)
            if not isinstance(value, str) or not COLOR.fullmatch(value):
                raise ValueError(f"{name} must be #rrggbb, got {value!r}.")
        if len(self.pages) != len(PERIODS):
            raise ValueError("a request needs exactly two pages of texts, Dec→Jun and Jun→Dec.")
        for page in self.pages:
            for name in ("title", "subtitle"):
                if len(getattr(page, name)) > MAX_TEXT_LENGTH:
                    raise ValueError(f"{name} is longer than {MAX_TEXT_LENGTH} characters.")


@dataclass
class SundialResult:
    pngs: list[bytes] = field(default_factory=list)  # one per half-year
    pdf: bytes = b""  # both half-years, one page each


def sanitize_image(data: bytes) -> bytes:
    """Decode an uploaded PNG or JPEG and re-encode it as a fresh PNG.

    Raises ``ValueError`` for anything else, or anything too large."""
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(f"image is larger than {MAX_IMAGE_BYTES // (1024 * 1024)} MB.")
    try:
        with Image.open(io.BytesIO(data)) as img:
            if img.format not in ("PNG", "JPEG"):
                raise ValueError(f"image must be PNG or JPEG, got {img.format}.")
            if max(img.size) > MAX_IMAGE_SIDE:  # checked before decoding the pixels
                raise ValueError(f"image is wider or taller than {MAX_IMAGE_SIDE} px.")
            clean = img.convert("RGBA")
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("image could not be read as PNG or JPEG.") from exc
    out = io.BytesIO()
    clean.save(out, format="PNG")
    return out.getvalue()


def _no_math(text: str) -> str:
    """Escape ``$`` so matplotlib shows it instead of parsing mathtext."""
    return text.replace("$", r"\$")


def _specs(request: SundialRequest, grid: GridConfig) -> list[SundialSpec]:
    tz_name = timezone_at(lat=request.lat, lng=request.lon) or "UTC"
    tz = ZoneInfo(tz_name)
    location = Location(lat=request.lat, lon=request.lon, timezone=tz_name)
    return [
        SundialSpec(
            location=location,
            timeframe=solstice_timeframe(request.year, period, tz),
            grid=grid,
            year=request.year,
            period=period,
        )
        for period in PERIODS
    ]


def _hints(request: SundialRequest, image_dir: Path | None) -> RenderHints:
    hints = replace(default_render_hints(), dayline_color=request.dayline_color, hourline_color=request.hourline_color)
    overlays = []
    for overlay in hints.overlays:
        upload = getattr(request, overlay.name, None)
        if upload is not None:
            if image_dir is None:
                raise ValueError("an uploaded image needs a folder to be written to.")
            path = image_dir / f"{overlay.name}.png"
            path.write_bytes(sanitize_image(upload))
            overlays.append(replace(overlay, image_path=str(path)))
        else:
            overlays.append(replace(overlay, image_path=resolve_image_path(overlay.image_path)))
    return replace(hints, overlays=overlays)


MapFn = Callable[[Callable[[SundialSpec], Plot], Iterable[SundialSpec]], Iterable[Plot]]


def build_pages(
    request: SundialRequest, grid: GridConfig = GRID, image_dir: Path | None = None, map_fn: MapFn = map
) -> list[tuple[Plot, RenderHints]]:
    """Compute both half-years; each plot carries its page's texts."""
    hints = _hints(request, image_dir)  # rejects a bad upload before the slow part
    plots = list(map_fn(build_plot, _specs(request, grid)))
    return [
        (replace(plot, title=_no_math(texts.title), subtitle=_no_math(texts.subtitle)), hints)
        for plot, texts in zip(plots, request.pages)
    ]


def make_sundial(request: SundialRequest, grid: GridConfig = GRID, map_fn: MapFn = map) -> SundialResult:
    """Both half-years as two PNG previews and one two-page PDF."""
    result = SundialResult()
    with tempfile.TemporaryDirectory(prefix="accuratum-") as tmp:
        pages = build_pages(request, grid=grid, image_dir=Path(tmp), map_fn=map_fn)
        pdf = io.BytesIO()
        with PdfPages(pdf) as doc:
            for plot, hints in pages:
                fig, _ = render(plot, hints)
                png = io.BytesIO()
                fig.savefig(png, format="png", dpi=PNG_DPI, bbox_inches="tight")
                result.pngs.append(png.getvalue())
                doc.savefig(fig, bbox_inches="tight")
    result.pdf = pdf.getvalue()
    return result
