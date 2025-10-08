from astropy import units as u
from datetime import datetime
from zoneinfo import ZoneInfo
from datetime import timedelta
# import astropy.coordinates

utc = ZoneInfo('UTC')

# Steps A - Dayline
# 0. move code related to initializing latitude and longitude to a specific function
# 1. Create a function to set the solstices days (current year + the last from previous year)
# 2. Create a function to set limiting days and day intervals, and timedelta for dayline
# 2.1. Create a function to build a single dayline
# 2.2 Modify the function above to build all daylines
# 3. Create a function to set limiting hours and time intervals, and timedelta for timeline
# 3.1. Create a function to build a single time
# 3.2 Modify the function above to build all timelines
# 4. Create a function to generate a matplotlib figure   <------ try to arrive here!
# 5. Create a function to set an image for the compass rose.
# 6. Create a function to set logo and position in the matplotlib

class DatetimeGrid:
    def __init__(self, longitude: float,
                 latitude: float,
                 current_datetime: datetime = datetime.now()
                 ):
        ...

    def set_solstices(self, date: datetime = datetime.now()):
        self.june_solstice = date.replace(month=6, day=21)
        self.december_solstice = date.replace(month=12, day=21)
        self.december_solstice_last_year = self.december_solstice.replace(year=date.year - 1)
        return



class AccuratumSolarClock (DatetimeGrid):

    def __init__(self, longitude: float, latitude: float, current_datetime: datetime = datetime.now()):
        super().__init__()

        self.set_location(longitude=longitude, latitude=latitude)
        self.current_datetime = current_datetime

        self.set_solstices(date=current_datetime)
        self.set_datetime_grid_edges()
        self.set_datetime_grid_spacings()

    def set_location(self, longitude: float, latitude: float,):
        if isinstance(longitude, float|int) and isinstance(longitude, float|int):
            self.lat = latitude*u.deg
            self.lon = longitude*u.deg
        else:
            msg = ( 'Accuratum: SolarClock initialization error. '
                    'Both longitude and latitude must be of type float'
                    f', received: {longitude}, {latitude}.'
            )
            raise TypeError(msg)
        return


    # TODO: move
    def set_datetime_grid_edges(self):

        self.daylines_start_time = datetime(year, month, day, hour=7, tzinfo=current_tz)
        self.daylines_end_time = datetime(year, month, day, hour=17, tzinfo=current_tz)



    def set_datetime_grid_spacings(self, daylines_interval: int | float | timedelta = timedelta(days = 7),
                          daylines_timedelta: int | float | timedelta = timedelta(minutes = 1),
                          timelines_interval: float | timedelta = timedelta(minutes = 10),
                          timelines_timedelta: int | float | timedelta = timedelta(hours = 24)
                          ):
        if not isinstance(daylines_interval, timedelta):
            self.dayline_interval = timedelta(days=daylines_interval)
        if not isinstance(daylines_timedelta, timedelta):
            self.dayline_timedelta = timedelta(minutes=daylines_timedelta)

        if not isinstance(timelines_interval, timedelta):
            self.timeline_interval = timedelta(minutes=timelines_interval)
        if not isinstance(timelines_timedelta, timedelta):
            self.timeline_timedelta = timedelta(hours=timelines_timedelta)
        return

    def set_solstices(self, date: datetime = datetime.now()):
        self.june_solstice = date.replace(month=6, day=21)
        self.december_solstice = date.replace(month=12, day=21)
        self.december_solstice_last_year = self.december_solstice.replace(year=date.year - 1)
        return

    def __str__(self):
        return "blu"


