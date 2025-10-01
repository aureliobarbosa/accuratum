from astropy import units as u
from datetime import datetime
from zoneinfo import ZoneInfo
from datetime import timedelta
# import astropy.coordinates

utc = ZoneInfo('UTC')

# TODO create a test for this function.
def get_solstices(date:datetime):
    year = date.year
    june_solstice = date.replace(year=year, month=6, day=21)
    december_solstice = date.replace(year=year, month=12, day=21)
    last_solstice_last_year = december_solstice.replace(year=date.year - 1)

    return last_solstice_last_year, june_solstice, december_solstice






class AccuratumSolarClock:
    # Coordinates for "Praça do cruzeiro, Brasilia, DF, Brazil"
    def __init__(self, longitude: float, latitude: float,
                 datetime: datetime = datetime.now(),
                 dayline_interval: int | float | timedelta = timedelta(days = 7),
                 dayline_timedelta: int | float | timedelta = timedelta(minutes = 1),
                 timeline_interval: float | timedelta = timedelta(minutes = 10),
                 timeline_timedelta: int | float | timedelta = timedelta(hours = 24),
                 ):

        if isinstance(longitude, float|int) and isinstance(longitude, float|int):
            self.lat = latitude*u.deg
            self.lon = longitude*u.deg
        else:
            msg = ( 'Accuratum: SolarClock initialization error. '
                    'Both longitude and latitude must be of type float'
                    f', received: {longitude}, {latitude}.'
            )
            raise TypeError(msg)

        self.current_datetime = datetime
        self.year = datetime.year
        self.month = datetime.month

        self.day = datetime.day

        if not isinstance(dayline_interval, timedelta):
            self.dayline_interval = timedelta(days=dayline_interval)
        if not isinstance(dayline_timedelta, timedelta):
            self.dayline_timedelta = timedelta(minutes=dayline_timedelta)

        if not isinstance(timeline_interval, timedelta):
            self.timeline_interval = timedelta(minutes=timeline_interval)
        if not isinstance(timeline_timedelta, timedelta):
            self.timeline_timedelta = timedelta(hours=timeline_timedelta)

        self.solstices = get_solstices(self.year)



