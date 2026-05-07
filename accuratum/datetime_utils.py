from datetime import datetime

DEFAULT_SOLSTICE_DAY = 21


def get_solstices(
    reference_datetime: datetime,
    solstice_day: int = DEFAULT_SOLSTICE_DAY,
) -> tuple[datetime, datetime, datetime]:
    """Return (previous-year December, current-year June, current-year December) solstices.

    The timezone of ``reference_datetime`` is preserved on all returned values.
    """
    tz = reference_datetime.tzinfo
    year = reference_datetime.year
    first = datetime(year - 1, 12, solstice_day, tzinfo=tz)
    middle = datetime(year, 6, solstice_day, tzinfo=tz)
    last = datetime(year, 12, solstice_day, tzinfo=tz)
    return first, middle, last


def frame_periods(
    solstices: tuple[datetime, datetime, datetime],
) -> list[list[datetime]]:
    """Split the three solstices into two consecutive [start, end] periods."""
    first, middle, last = solstices
    return [[first, middle], [middle, last]]
