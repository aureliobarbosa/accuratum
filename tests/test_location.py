import pytest
from geopy.exc import GeocoderQueryError, GeocoderTimedOut, GeocoderUnavailable

from accuratum.location import location_to_latitude_longitude


@pytest.mark.parametrize(
    "location_string, expected_lat, expected_lon",
    [
        ("Praça do Cruzeiro, Brasília, Brazil", -15.7833, -47.8667),
        ("Paris, France", 48.8566, 2.3522),
    ],
)
def test_existing_location(mocker, location_string, expected_lat, expected_lon):
    fake_location = mocker.Mock(latitude=expected_lat, longitude=expected_lon)
    nominatim_cls = mocker.patch("accuratum.location.Nominatim")
    nominatim_cls.return_value.geocode.return_value = fake_location

    latlon = location_to_latitude_longitude(
        location_string=location_string,
        project="AccuratumTest",
        user="AccuratumDev",
    )

    assert latlon is not None, f"TestError: Could not find existing location '{location_string}'."
    latitude, longitude = latlon
    assert isinstance(latitude, float), f"TestError: variable latitude should be a float, but is of {type(latitude)}."
    assert isinstance(longitude, float), (
        f"TestError: variable longitude should be a float, but is of {type(longitude)}."
    )
    assert (latitude, longitude) == (expected_lat, expected_lon)
    nominatim_cls.assert_called_once_with(user_agent="AccuratumTest-AccuratumDev")
    nominatim_cls.return_value.geocode.assert_called_once_with(location_string)


@pytest.mark.parametrize("location_string", ["NonExistentPlaceXYZ123"])
def test_non_existing_location(mocker, location_string):
    nominatim_cls = mocker.patch("accuratum.location.Nominatim")
    nominatim_cls.return_value.geocode.return_value = None

    latlon = location_to_latitude_longitude(
        location_string=location_string,
        project="AccuratumTest",
        user="AccuratumDev",
    )

    assert latlon is None, f"TestError: Found previously inexistent location {location_string}."


def test_malformed_query_raises_value_error(mocker):
    nominatim_cls = mocker.patch("accuratum.location.Nominatim")
    nominatim_cls.return_value.geocode.side_effect = GeocoderQueryError("bad query")

    with pytest.raises(ValueError):
        location_to_latitude_longitude(
            location_string="??malformed??",
            project="AccuratumTest",
            user="AccuratumDev",
        )


@pytest.mark.parametrize(
    "exc",
    [GeocoderTimedOut("timeout"), GeocoderUnavailable("unavailable")],
)
def test_service_error_is_reraised(mocker, exc):
    nominatim_cls = mocker.patch("accuratum.location.Nominatim")
    nominatim_cls.return_value.geocode.side_effect = exc

    with pytest.raises(type(exc)):
        location_to_latitude_longitude(
            location_string="Paris, France",
            project="AccuratumTest",
            user="AccuratumDev",
        )
