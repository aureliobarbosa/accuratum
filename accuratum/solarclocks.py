from astropy import units as u
from datetime import datetime
from zoneinfo import ZoneInfo
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
    def __init__(self, longitude: float, latitude: float, datetime: datetime = datetime.now()):

        if isinstance(longitude, float) and isinstance(longitude, float):
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

        # Default values











