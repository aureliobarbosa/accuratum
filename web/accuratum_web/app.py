"""The FastAPI app: the sundial API and the static page.

One route does the work: ``POST /api/sundial`` takes the form of
web/docs/UX.md and returns both half-years as base64 PNGs and a PDF.
"""

import asyncio
import base64
import threading
import time
from collections import defaultdict, deque
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager
from multiprocessing import get_context
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import UploadFile

from accuratum.core.spec import GridConfig
from accuratum.defaults.overlays import ACCURATUM_LOGO, DEFAULT_OVERLAYS, resolve_image_path
from accuratum_web.sundial import GRID, MAX_IMAGE_BYTES, PageTexts, SundialRequest, make_sundial

MAX_REQUEST_BYTES = 2 * MAX_IMAGE_BYTES + 64 * 1024  # two uploads plus the text fields
TIMEOUT_SECONDS = 50.0  # under the 60 s of Cloud Run and Firebase Hosting
WORKERS = 2  # one process per half-year
MAX_CONCURRENT = 1  # sundials computed at once per instance (~260 MB each)
RATE_LIMIT = (6, 600.0)  # sundials per client per 10 minutes
STATIC_DIR = Path(__file__).parent / "static"
# Package images the page shows: the form's default logo and compass, and the
# project's logo on the landing page. Served from the package, not copied.
PACKAGE_IMAGES = {
    "logo": DEFAULT_OVERLAYS["logo"].image_path,
    "compass": DEFAULT_OVERLAYS["compass"].image_path,
    "accuratum": ACCURATUM_LOGO,
}

# The page loads only its own files. The exceptions: OpenStreetMap tiles for
# the map, Nominatim for the place search (run from the visitor's browser),
# and data: URIs for the PNG previews.
CSP = "; ".join(
    [
        "default-src 'self'",
        "img-src 'self' data: https://tile.openstreetmap.org",
        "connect-src 'self' https://nominatim.openstreetmap.org",
        "object-src 'none'",
        "base-uri 'none'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)
SECURITY_HEADERS = {
    "Content-Security-Policy": CSP,
    "X-Content-Type-Options": "nosniff",
    # OSM's tile policy needs a Referer; send only the origin to other sites.
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


class Busy(Exception):
    pass


class RateLimiter:
    """At most *limit* hits per client in a sliding *window* of seconds. In memory, per instance."""

    def __init__(self, limit: int, window: float) -> None:
        self.limit, self.window = limit, window
        self.hits: dict[str, deque[float]] = defaultdict(deque)
        self.lock = threading.Lock()

    def allow(self, client: str) -> bool:
        now = time.monotonic()
        with self.lock:
            hits = self.hits[client]
            while hits and hits[0] <= now - self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True


def _client(request: Request) -> str:
    # Behind Firebase Hosting the CDN (Fastly) calls Cloud Run, and the visitor
    # is in Fastly-Client-Ip. Called on run.app directly, the visitor is the
    # first X-Forwarded-For entry. Both can be forged to dodge one's own limit;
    # the per-instance concurrency cap and max instances still bound the load.
    fastly = request.headers.get("fastly-client-ip", "").strip()
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    return fastly or forwarded or (request.client.host if request.client else "unknown")


def _request_from_form(form, uploads: dict[str, bytes | None]) -> SundialRequest:
    try:
        return SundialRequest(
            lat=float(form["lat"]),
            lon=float(form["lon"]),
            year=int(form["year"]),
            dayline_color=form["dayline_color"],
            hourline_color=form["hourline_color"],
            pages=tuple(PageTexts(form.get(f"title{i}", ""), form.get(f"subtitle{i}", "")) for i in (0, 1)),
            **uploads,
        )
    except KeyError as exc:
        raise ValueError(f"missing field {exc.args[0]!r}.") from None


def create_app(
    grid: GridConfig = GRID,
    workers: int = WORKERS,
    timeout_seconds: float = TIMEOUT_SECONDS,
    max_concurrent: int = MAX_CONCURRENT,
    rate_limit: tuple[int, float] = RATE_LIMIT,
) -> FastAPI:
    """``workers=0`` computes the two half-years one after the other, in the request's thread."""
    slots = threading.BoundedSemaphore(max_concurrent)
    limiter = RateLimiter(*rate_limit)
    pool: dict[str, ProcessPoolExecutor] = {}

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if workers:
            # spawn, not fork: forking a threaded server can copy held locks.
            pool["executor"] = ProcessPoolExecutor(max_workers=workers, mp_context=get_context("spawn"))
        yield
        if pool:
            pool.pop("executor").shutdown(cancel_futures=True)

    app = FastAPI(title="Accuratum", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)

    def compute(request: SundialRequest):
        # The slot is held for as long as the computation really runs, even
        # after the client got its 504, so the cap on concurrent work holds.
        if not slots.acquire(timeout=timeout_seconds):
            raise Busy
        try:
            map_fn = pool["executor"].map if pool else map
            return make_sundial(request, grid=grid, map_fn=map_fn)
        finally:
            slots.release()

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.update(SECURITY_HEADERS)
        return response

    @app.middleware("http")
    async def limit_request_size(request: Request, call_next):
        if request.method == "POST":
            length = request.headers.get("content-length")
            if length is None:
                return JSONResponse({"detail": "Content-Length required."}, status_code=411)
            if not length.isdigit() or int(length) > MAX_REQUEST_BYTES:
                return JSONResponse({"detail": "request too large."}, status_code=413)
        return await call_next(request)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/image/{name}")
    def package_image(name: str):
        if name not in PACKAGE_IMAGES:
            return JSONResponse({"detail": "not found."}, status_code=404)
        return FileResponse(resolve_image_path(PACKAGE_IMAGES[name]))

    @app.post("/api/sundial")
    async def sundial(request: Request):
        if not limiter.allow(_client(request)):
            return JSONResponse({"detail": "too many sundials; try again in a few minutes."}, status_code=429)
        async with request.form(max_files=2, max_fields=20) as form:
            uploads = {}
            for name in ("logo", "compass"):
                item = form.get(name)
                uploads[name] = await item.read(MAX_IMAGE_BYTES + 1) if isinstance(item, UploadFile) else None
            try:
                sundial_request = _request_from_form(form, uploads)
            except ValueError as exc:
                return JSONResponse({"detail": str(exc)}, status_code=422)
        try:
            result = await asyncio.wait_for(run_in_threadpool(compute, sundial_request), timeout_seconds)
        except ValueError as exc:
            return JSONResponse({"detail": str(exc)}, status_code=422)
        except (asyncio.TimeoutError, Busy):
            return JSONResponse({"detail": "the server is busy; try again in a minute."}, status_code=504)
        return {
            "pngs": [base64.b64encode(png).decode("ascii") for png in result.pngs],
            "pdf": base64.b64encode(result.pdf).decode("ascii"),
        }

    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    return app


app = create_app()
