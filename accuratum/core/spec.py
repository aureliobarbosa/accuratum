"""Sundial specification — the JSON-roundtrippable input to ``build_plot``.

A ``SundialSpec`` is pure data: location, timeframe and knobs. It
contains no astropy or matplotlib objects.

JSON-roundtrip is provided by :func:`spec_to_dict` and :func:`spec_from_dict`.
``json.dumps`` silently converts tuples to lists, so those helpers also
re-tuplize on the way back and rebuild nested dataclasses.

Rendering concerns (overlay images, canvas size, fonts) live in
:mod:`accuratum.core.hints`, not here: they don't change the geometry, so
they stay out of :func:`spec_hash`. A saved project keeps both (see
:mod:`accuratum.core.project`).
"""

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, tzinfo
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# Past ~75.5° the summer sun stays above the 10° horizon cut nearly all day,
# and the hour lines of one clock hour start to repeat. Up to here the dial
# is only shortened: the winter weeks with the sun below the cut drop out.
MAX_LATITUDE = 75.0

# The solstices are approximated as the 21st of June and December.
SOLSTICE_DAY = 21

# Input bounds. Specs come from project files and web requests, so each
# value is checked: one spec must not be able to exhaust a server.
MIN_YEAR, MAX_YEAR = 1901, 2100  # ERFA's Earth ephemeris (epv00) covers 1900-2100
MAX_TIMEFRAME_DAYS = 366
LINE_POINTS_RANGE = (2, 10_000)
TIME_STEP_MINUTES_RANGE = (1, 240)
DAY_STEP_RANGE = (1, 183)
HORIZON_DEGREES_RANGE = (0.0, 45.0)


def _check_int(name: str, value: Any, low: int, high: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
        raise ValueError(f"{name} must be an integer from {low} to {high}, got {value!r}.")


def _check_number(name: str, value: Any, low: float = -math.inf, high: float = math.inf) -> None:
    ok = isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    if not ok or not low <= value <= high:
        raise ValueError(f"{name} must be a finite number from {low:g} to {high:g}, got {value!r}.")


@dataclass(frozen=True)
class Location:
    lat: float
    lon: float
    timezone: str
    name: str | None = None

    def __post_init__(self) -> None:
        _check_number("lat", self.lat)
        if abs(self.lat) > MAX_LATITUDE:
            raise ValueError(f"latitude {self.lat:g}° is outside the supported range ±{MAX_LATITUDE:g}°.")
        _check_number("lon", self.lon, -180.0, 180.0)
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError, TypeError):
            raise ValueError(f"timezone {self.timezone!r} is not a known IANA time zone.") from None


@dataclass(frozen=True)
class TimeFrame:
    """Closed interval ``[start, end]`` as timezone-aware datetimes."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("TimeFrame.start and TimeFrame.end must be timezone-aware.")
        days = (self.end - self.start).total_seconds() / 86400
        if not 0 < days <= MAX_TIMEFRAME_DAYS:
            raise ValueError(f"timeframe end must come after its start, at most {MAX_TIMEFRAME_DAYS} days later.")


@dataclass(frozen=True)
class GridConfig:
    dayline_day_step_days: int = 7
    line_points: int = 500
    hourline_day_step_days: int = 1
    time_step_minutes: int = 20
    horizon_degrees: float = 10.0

    def __post_init__(self) -> None:
        _check_int("dayline_day_step_days", self.dayline_day_step_days, *DAY_STEP_RANGE)
        _check_int("line_points", self.line_points, *LINE_POINTS_RANGE)
        _check_int("hourline_day_step_days", self.hourline_day_step_days, *DAY_STEP_RANGE)
        _check_int("time_step_minutes", self.time_step_minutes, *TIME_STEP_MINUTES_RANGE)
        _check_number("horizon_degrees", self.horizon_degrees, *HORIZON_DEGREES_RANGE)


@dataclass
class SundialSpec:
    """Everything needed to compute the sundial's geometry.

    ``timeframe`` is what the computation uses. ``year`` and ``period`` are
    the CLI options that produced it (``None`` for a hand-built timeframe).
    """

    location: Location
    timeframe: TimeFrame
    plumb_length: float = 1.0
    grid: GridConfig = field(default_factory=GridConfig)
    sundial_type: str = "accuratum"
    year: int | None = None
    period: int | None = None

    def __post_init__(self) -> None:
        _check_number("plumb_length", self.plumb_length)
        if self.plumb_length <= 0:
            raise ValueError(f"plumb_length must be positive, got {self.plumb_length!r}.")
        if self.year is not None:
            _check_int("year", self.year, MIN_YEAR, MAX_YEAR)
        if self.period not in (None, 0, 1) or isinstance(self.period, bool):
            raise ValueError(f"period must be 0 or 1, got {self.period!r}.")


def solstice_timeframe(year: int, period: int, tz: tzinfo) -> TimeFrame:
    """The solstice-to-solstice frame: period 0 is Dec(year-1)→Jun(year), 1 is Jun→Dec(year)."""
    dec_prev = datetime(year - 1, 12, SOLSTICE_DAY, tzinfo=tz)
    jun_curr = datetime(year, 6, SOLSTICE_DAY, tzinfo=tz)
    dec_curr = datetime(year, 12, SOLSTICE_DAY, tzinfo=tz)
    if period == 0:
        return TimeFrame(start=dec_prev, end=jun_curr)
    if period == 1:
        return TimeFrame(start=jun_curr, end=dec_curr)
    raise ValueError(f"period must be 0 or 1, got {period!r}.")


# --- JSON-roundtrip helpers --------------------------------------------------


def spec_to_dict(spec: SundialSpec) -> dict[str, Any]:
    """Convert *spec* to a JSON-ready dict (datetimes as ISO strings)."""
    data = asdict(spec)
    data["timeframe"]["start"] = spec.timeframe.start.isoformat()
    data["timeframe"]["end"] = spec.timeframe.end.isoformat()
    return data


def spec_from_dict(data: dict[str, Any]) -> SundialSpec:
    """Inverse of :func:`spec_to_dict`. Re-tuplizes and rebuilds frozen subobjects.

    Raises ``ValueError`` for any bad input, malformed or out of bounds."""
    try:
        loc = Location(**data["location"])
        tf = TimeFrame(
            start=datetime.fromisoformat(data["timeframe"]["start"]),
            end=datetime.fromisoformat(data["timeframe"]["end"]),
        )
        grid = GridConfig(**data.get("grid", {}))
        return SundialSpec(
            location=loc,
            timeframe=tf,
            plumb_length=data.get("plumb_length", 1.0),
            grid=grid,
            sundial_type=data.get("sundial_type", "accuratum"),
            year=data.get("year"),
            period=data.get("period"),
        )
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError(f"malformed spec: {exc!r}") from exc


def spec_hash(spec: SundialSpec) -> str:
    """SHA-256 of *spec*'s canonical JSON. ``location.name`` is left out: it
    doesn't change the geometry, so renaming a place never invalidates a
    saved dataset."""
    data = spec_to_dict(spec)
    data["location"].pop("name", None)
    blob = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
