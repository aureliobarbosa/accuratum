import base64
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from accuratum.core.spec import GridConfig
from accuratum_web.app import MAX_REQUEST_BYTES, app, create_app

FAST_GRID = GridConfig(dayline_day_step_days=30, line_points=20, hourline_day_step_days=10, time_step_minutes=60)

FORM = {
    "lat": "-15.78",
    "lon": "-47.92",
    "year": "2026",
    "dayline_color": "#d55e00",
    "hourline_color": "#0072b2",
    "title0": "UnB",
    "subtitle0": "dez–jun",
    "title1": "UnB",
    "subtitle1": "jun–dez",
}


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app(grid=FAST_GRID, workers=0, rate_limit=(1000, 60.0))) as c:
        yield c


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (40, 20), (200, 30, 30)).save(buf, format="PNG")
    return buf.getvalue()


def test_health():
    with TestClient(app) as c:
        response = c.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_sundial_returns_two_pngs_and_a_pdf(client):
    response = client.post("/api/sundial", data=FORM, files={"logo": ("logo.png", _png(), "image/png")})
    assert response.status_code == 200, response.text
    body = response.json()
    assert [base64.b64decode(p)[:4] for p in body["pngs"]] == [b"\x89PNG", b"\x89PNG"]
    assert base64.b64decode(body["pdf"])[:4] == b"%PDF"


@pytest.mark.parametrize(
    "field, value",
    [("dayline_color", "red"), ("lat", "80"), ("lat", "nan"), ("year", "3000"), ("title0", "x" * 81)],
)
def test_invalid_input_is_a_422_with_a_message(client, field, value):
    response = client.post("/api/sundial", data={**FORM, field: value})
    assert response.status_code == 422
    assert response.json()["detail"]


def test_missing_field_is_a_422(client):
    form = {k: v for k, v in FORM.items() if k != "lat"}
    assert client.post("/api/sundial", data=form).status_code == 422


def test_bad_upload_is_a_422(client):
    response = client.post("/api/sundial", data=FORM, files={"compass": ("x.svg", b"<svg/>", "image/svg+xml")})
    assert response.status_code == 422
    assert "image" in response.json()["detail"]


def test_oversized_request_is_a_413(client):
    big = b"0" * (MAX_REQUEST_BYTES + 1)
    response = client.post("/api/sundial", data=FORM, files={"logo": ("logo.png", big, "image/png")})
    assert response.status_code == 413


def test_slow_request_times_out_with_a_504():
    with TestClient(create_app(grid=FAST_GRID, workers=0, timeout_seconds=0.01)) as c:
        response = c.post("/api/sundial", data=FORM)
    assert response.status_code == 504


def test_parallel_workers_give_the_same_pages():
    with TestClient(create_app(grid=FAST_GRID, workers=2)) as c:
        response = c.post("/api/sundial", data=FORM)
    assert response.status_code == 200, response.text
    assert len(response.json()["pngs"]) == 2


# --- security headers, rate limit, static page -------------------------------


def test_security_headers_on_every_response(client):
    for path in ("/api/health", "/"):
        headers = client.get(path).headers
        csp = headers["content-security-policy"]
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "object-src 'none'" in csp
        assert headers["x-content-type-options"] == "nosniff"
        assert headers["referrer-policy"] == "strict-origin-when-cross-origin"


def test_csp_allows_only_the_map_tiles_and_place_search():
    from accuratum_web.app import CSP

    assert "img-src 'self' data: https://tile.openstreetmap.org" in CSP
    assert "connect-src 'self' https://nominatim.openstreetmap.org" in CSP
    assert "unsafe-inline" not in CSP and "unsafe-eval" not in CSP


def test_sundial_requests_are_rate_limited_per_client():
    with TestClient(create_app(grid=FAST_GRID, workers=0, rate_limit=(1, 60.0))) as c:
        assert c.post("/api/sundial", data=FORM).status_code == 200
        response = c.post("/api/sundial", data=FORM)
        assert response.status_code == 429
        assert c.get("/api/health").status_code == 200  # only the costly route is limited


def test_the_page_is_served_at_the_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


@pytest.mark.parametrize("name, magic", [("logo", b"\xff\xd8"), ("compass", b"\x89PNG"), ("accuratum", b"\x89PNG")])
def test_package_images_are_served(client, name, magic):
    response = client.get(f"/api/image/{name}")
    assert response.status_code == 200
    assert response.content.startswith(magic)


def test_only_the_named_images_are_served(client):
    assert client.get("/api/image/..%2F..%2Fetc%2Fpasswd").status_code == 404
    assert client.get("/api/image/unknown").status_code == 404
