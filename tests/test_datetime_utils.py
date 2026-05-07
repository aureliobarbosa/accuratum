from datetime import datetime
from zoneinfo import ZoneInfo

from accuratum.datetime_utils import frame_periods, get_solstices

TZ_SP = ZoneInfo("America/Sao_Paulo")


def test_get_solstices_returns_three_datetimes():
    reference = datetime(2026, 4, 14, tzinfo=TZ_SP)
    first, middle, last = get_solstices(reference)

    assert first.year == 2025
    assert first.month == 12
    assert first.day == 21
    assert middle.year == 2026
    assert middle.month == 6
    assert middle.day == 21
    assert last.year == 2026
    assert last.month == 12
    assert last.day == 21


def test_get_solstices_preserves_timezone():
    reference = datetime(2026, 4, 14, tzinfo=TZ_SP)
    first, middle, last = get_solstices(reference)
    for s in (first, middle, last):
        assert s.tzinfo == TZ_SP


def test_get_solstices_custom_day():
    reference = datetime(2026, 4, 14, tzinfo=TZ_SP)
    first, middle, last = get_solstices(reference, solstice_day=20)
    assert first.day == middle.day == last.day == 20


def test_frame_periods_returns_two_pairs():
    reference = datetime(2026, 4, 14, tzinfo=TZ_SP)
    solstices = get_solstices(reference)
    periods = frame_periods(solstices)

    assert len(periods) == 2
    assert len(periods[0]) == 2
    assert len(periods[1]) == 2
    # First pair: dec prev -> jun current
    assert periods[0][0] == solstices[0]
    assert periods[0][1] == solstices[1]
    # Second pair: jun current -> dec current
    assert periods[1][0] == solstices[1]
    assert periods[1][1] == solstices[2]
