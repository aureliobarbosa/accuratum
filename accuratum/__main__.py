from datetime import datetime
from zoneinfo import ZoneInfo

from accuratum.astronomy import compute_blocks
from accuratum.datetime_utils import (
    build_dayline_grid,
    build_hourline_grid,
    frame_periods,
    get_solstices,
)


def main():
    lat, lon = -15.783507525862756, -47.91526919090653
    tz = ZoneInfo("America/Sao_Paulo")

    periods = frame_periods(get_solstices(datetime.now(tz=tz)))
    daylines = build_dayline_grid(periods[0])
    hourlines = build_hourline_grid(periods[0])

    blocks_x, blocks_y = compute_blocks(daylines, hourlines, lat=lat, lon=lon)
    print(f"Accuratum CLI computed {len(blocks_x)} blocks.")


if __name__ == "__main__":
    main()
