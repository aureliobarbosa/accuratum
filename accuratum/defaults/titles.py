"""Default title and subtitle texts, used when the project doesn't set its own.

They are resolved at render time, not saved: renaming ``location.name`` in
``project.json`` renames a default title too.
"""

from accuratum.core.spec import SundialSpec


def default_title(spec: SundialSpec) -> str:
    """The location name, or its coordinates when it has none (``--lat-long``)."""
    loc = spec.location
    if loc.name:
        return loc.name
    ns = "S" if loc.lat < 0 else "N"
    ew = "W" if loc.lon < 0 else "E"
    return f"{abs(loc.lat):.2f}° {ns}, {abs(loc.lon):.2f}° {ew}"


def default_subtitle(spec: SundialSpec) -> str:
    """The timeframe as ``yyyy-mm-dd / yyyy-mm-dd``."""
    return f"{spec.timeframe.start:%Y-%m-%d} / {spec.timeframe.end:%Y-%m-%d}"
