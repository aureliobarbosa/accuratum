from typing import Optional, Tuple

from geopy.exc import (
    GeocoderParseError,
    GeocoderQueryError,
    GeocoderServiceError,
    GeocoderTimedOut,
    GeocoderUnavailable,
)
from geopy.geocoders import Nominatim

_GEO_SERVICE_ERRORS = (
    GeocoderParseError,
    GeocoderServiceError,
    GeocoderTimedOut,
    GeocoderUnavailable,
)


def location_to_latitude_longitude(
    location_string: str, user: str = "Anonymous", project: str = "Accuratum"
) -> Optional[Tuple[float, float]]:
    """
    Converts a location string to latitude and longitude coordinates.

    Args:
        location_string (str): The string representing the location (e.g., "Praça do Cruzeiro, Brasília, Brazil").
        user (str): An identifier for the user or specific part of the application.
                    Defaults to "Anonymous".
        project (str): The name of your project. This will be used in the user_agent string.
                       Defaults to "Accuratum".

    Returns:
        Tuple[ float, float]:: A tuple containing (latitude, longitude) if successful,
                                        or None, if the location cannot be found.
    """
    user_agent = f"{project}-{user}"
    geolocator = Nominatim(user_agent=user_agent)

    try:
        location = geolocator.geocode(location_string)

        if location is not None:
            return location.latitude, location.longitude
        else:
            return None
    except GeocoderQueryError as e:
        print(f"AccuratumError: the string '{location_string}' is possibly malformed!")
        print("An error been catched and will be raised again. Check backtrace for more information.")
        print("Geopy Error Message:\n", e)
        raise ValueError(f"Package geopy could not identify the string: ''{location_string}")
    except _GEO_SERVICE_ERRORS as e:
        print("AccuratumError: a service problem has occurred and has been catched by geopy.")
        print("An error been catched and will be raised again. Check backtrace for more information.")
        raise e


