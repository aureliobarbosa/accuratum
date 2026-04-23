import pytest

from accuratum.location import location_to_latitude_longitude


@pytest.mark.parametrize(
    "location_string",
    [
        "Praça do Cruzeiro, Brasília, Brazil",
        "Paris",
    ],
)
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

    assert latlon is not None, f"TestError: Could not find existing location '{location_string}'."
    assert isinstance(latitude, float), f"TestError: variable latitude should be a float, but is of {type(latitude)}."
    assert isinstance(longitude, float), (
        f"TestError: variable longitude should be a float, but is of {type(longitude)}."
    )


@pytest.mark.parametrize("location_string", ["NonExistentPlaceXYZ123"])
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

    assert latlon is None, f"TestError: Found previously inexistent location {location_string}."
