from typing import Optional, Tuple

from geopy.exc import (
    GeocoderParseError,
    GeocoderServiceError,
    GeocoderTimedOut,
    GeocoderUnavailable,
)
from geopy.geocoders import Nominatim
from geopy.location import Location


def convert_place_to_latitude_longitude(
    location_string: str, user: str = "Anonymous", project: str = "geopy-project"
) -> Tuple[Optional[float], Optional[float]]:
    """
    Converts a location string to latitude and longitude coordinates.

    Args:
        location_string (str): The string representing the location (e.g., "Praça do Cruzeiro, Brasília, Brazil").
        user (str): An identifier for the user or specific part of the application.
                    Defaults to "Anonymous".
        project (str): The name of your project. This will be used in the user_agent string.
                       Defaults to "geopy-project".

    Returns:
        Tuple[Optional[float], Optional[float]]: A tuple containing (latitude, longitude) if successful.
                                                  If an error occurs, returns (None, None).
    """
    user_agent = f"{project}-{user}"
    geolocator = Nominatim(user_agent=user_agent)

    try:
        location: Optional[Location] = geolocator.geocode(location_string)

        if location:
            return location.latitude, location.longitude
        else:
            # If location is None, it means no result was found
            return None, None
    except GeocoderTimedOut:
        return None, None
    except GeocoderServiceError:
        return None, None
    except GeocoderUnavailable:
        return None, None
    except GeocoderParseError:
        return None, None
    except Exception:
        # Catch any other unexpected exceptions
        return None, None


if __name__ == "__main__":
    # Example Usage:
    lat, lon = convert_place_to_latitude_longitude(
        location_string="Praça do Cruzeiro, Brasília, Brazil",
        project="MyAstropyApp",
        user="TestUser1",
    )
    if lat is not None and lon is not None:
        print(f"Praça do Cruzeiro, Brasília, Brazil: Latitude={lat}, Longitude={lon}")
    else:
        print(
            "Could not get coordinates for Praça do Cruzeiro, Brasília, Brazil or an error occurred."
        )

    lat, lon = convert_place_to_latitude_longitude(
        location_string="NonExistentPlaceXYZ123",
        project="MyAstropyApp",
        user="TestUser2",
    )
    if lat is not None and lon is not None:
        print(f"NonExistentPlaceXYZ123: Latitude={lat}, Longitude={lon}")
    else:
        print(
            "Could not get coordinates for NonExistentPlaceXYZ123 or an error occurred."
        )

    # Example of a potentially problematic request (e.g., very vague)
    lat, lon = convert_place_to_latitude_longitude(
        location_string="Paris", project="MyAstropyApp", user="TestUser3"
    )
    if lat is not None and lon is not None:
        print(f"Paris: Latitude={lat}, Longitude={lon}")
    else:
        print("Could not get coordinates for Paris or an error occurred.")

    # You could also add a test for a service error by e.g. using a fake URL in Nominatim if you were truly testing
    # Or by triggering a timeout by setting a very short timeout on Nominatim in a test environment.
