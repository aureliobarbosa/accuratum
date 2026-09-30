"""The FastAPI app: the sundial API and the static page.

One route does the work: ``POST /api/sundial`` takes the form of
web/docs/UX.md and returns both half-years as base64 PNGs and a PDF.
"""

import asyncio
import base64
import threading
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager
from multiprocessing import get_context

from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from starlette.datastructures import UploadFile

from accuratum.core.spec import GridConfig
from accuratum_web.sundial import GRID, MAX_IMAGE_BYTES, PageTexts, SundialRequest, make_sundial

MAX_REQUEST_BYTES = 2 * MAX_IMAGE_BYTES + 64 * 1024  # two uploads plus the text fields
TIMEOUT_SECONDS = 50.0  # under the 60 s of Cloud Run and Firebase Hosting
WORKERS = 2  # one process per half-year
MAX_CONCURRENT = 1  # sundials computed at once per instance (~260 MB each)


class Busy(Exception):
    pass


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
) -> FastAPI:
    """``workers=0`` computes the two half-years one after the other, in the request's thread."""
    slots = threading.BoundedSemaphore(max_concurrent)
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

    @app.post("/api/sundial")
    async def sundial(request: Request):
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

    return app


app = create_app()
