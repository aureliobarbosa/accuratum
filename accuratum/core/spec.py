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
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Location:
    lat: float
    lon: float
    timezone: str
    name: str | None = None


@dataclass(frozen=True)
class TimeFrame:
    """Closed interval ``[start, end]`` as timezone-aware datetimes."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("TimeFrame.start and TimeFrame.end must be timezone-aware.")


@dataclass(frozen=True)
class GridConfig:
    dayline_day_step_days: int = 7
    line_points: int = 500
    hourline_day_step_days: int = 1
    time_step_minutes: int = 20
    horizon_degrees: float = 10.0


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


# --- JSON-roundtrip helpers --------------------------------------------------


def spec_to_dict(spec: SundialSpec) -> dict[str, Any]:
    """Convert *spec* to a JSON-ready dict (datetimes as ISO strings)."""
    data = asdict(spec)
    data["timeframe"]["start"] = spec.timeframe.start.isoformat()
    data["timeframe"]["end"] = spec.timeframe.end.isoformat()
    return data


def spec_from_dict(data: dict[str, Any]) -> SundialSpec:
    """Inverse of :func:`spec_to_dict`. Re-tuplizes and rebuilds frozen subobjects."""
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


def spec_hash(spec: SundialSpec) -> str:
    """SHA-256 of *spec*'s canonical JSON. ``location.name`` is left out: it
    doesn't change the geometry, so renaming a place never invalidates a
    saved dataset."""
    data = spec_to_dict(spec)
    data["location"].pop("name", None)
    blob = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
