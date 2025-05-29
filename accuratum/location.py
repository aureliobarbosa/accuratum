import time
from typing import Optional, Tuple, TypeAlias

from geopy.exc import (
    GeocoderParseError,
    GeocoderQueryError,
    GeocoderServiceError,
    GeocoderTimedOut,
    GeocoderUnavailable,
)
from geopy.geocoders import Nominatim
from geopy.location import Location

GeoException: TypeAlias = (
    GeocoderParseError | GeocoderServiceError | GeocoderTimedOut | GeocoderUnavailable
)


def location_to_latitude_longitude(
    location_string: str, user: str = "Anonymous", project: str = "Accuratum"
) -> Tuple[float, float] | None:
    """
    Converts a location string to latitude and longitude coordinates.

    Args:
        location_string (str): The string representing the location (e.g., "Praça do Cruzeiro, Brasília, Brazil").
        user (str): An identifier for the user or specific part of the application.
                    Defaults to "Anonymous".
        project (str): The name of your project. This will be used in the user_agent string.
                       Defaults to "Accuratum".

    Returns:
        Tuple[ float, float] | None:: A tuple containing (latitude, longitude) if successful,
                                                  or None, if the location cannot be found.
    """
    user_agent = f"{project}-{user}"
    geolocator = Nominatim(user_agent=user_agent)

    try:
        location: Location | None = geolocator.geocode(location_string)

        if location:
            return location.latitude, location.longitude
        else:
            return None
    except GeoException as e:
        print("A service problem has occurred.")
        raise e
    except GeocoderQueryError as e:
        print(f"The string '{location_string}' is possibly malformed!")


def test_existing_location(location_string):
    project_test = "AccuratumTest"
    user_test = "AccuratumDev"

    latlon = location_to_latitude_longitude(
        location_string=location_string,
        project=project_test,
        user=user_test,
    )
    if latlon:
        latitude, longitude = latlon
        print(f"{location_string}: Latitude={latitude}, Longitude={longitude}")

    assert latlon is not None, "TestError: Could not find existing location '{location_string}'."
    assert isinstance(latitude, float), "TestError: variable latitude should be a float, but is of {type(latitude)}."
    assert isinstance(longitude, float), "TestError: variable langitude should be a float, but is of {type(latitude)}."

def test_non_existing_location(location_string):
    project_test = "AccuratumTest"
    user_test = "AccuratumDev"

    latlon = location_to_latitude_longitude(
        location_string=location_string,
        project=project_test,
        user=user_test,
    )
    if latlon is None:
        print(f"location {location_string} does not exist, as expected.")
    else:
        latitude, longitude = latlon
        print(f"found previously inexistent location {location_string} at {latitude},{longitude}.")

    assert latlon is None, "TestError: Found previously inexistent location {location_string} at {latitude},{longitude}."



# def test_non_existing_location(location_string):

if __name__ == "__main__":
    location_string = "Praça do Cruzeiro, Brasília, Brazil"
    test_existing_location(location_string)
    
    location_string = "Paris"
    test_existing_location(location_string)

    location_string="NonExistentPlaceXYZ123"
    test_non_existing_location(location_string)
