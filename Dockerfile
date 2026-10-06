# The website's image: FastAPI (web/) plus the library, nothing else.
#
# Two stages on the SAME base. `build` makes the venv and `runtime` copies it.
# A venv isn't relocable between Python installs: it records the
# interpreter's absolute path and holds extensions built for one libc.
# Python 3.11 is the baseline that CI tests.
#
# Both packages go in as wheels (--no-editable), so the runtime stage needs
# no source tree: the library's fig/ and the site's static/ live in the venv.
#
# uv comes in by `COPY --from` with a fixed version; the uv.lock pins only
# the dependencies, not the tool.
ARG UV_VERSION=0.12.23
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

# --- build -----------------------------------------------------------------
FROM python:3.11-slim-bookworm AS build
COPY --from=uv /uv /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app
# Dependencies first, in their own layer: they change far less than the code.
# README.md and LICENSE.md because the library's pyproject.toml points at them.
COPY pyproject.toml uv.lock README.md LICENSE.md ./
COPY web/pyproject.toml web/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package accuratum-web --no-install-workspace

COPY accuratum/ accuratum/
COPY web/accuratum_web/ web/accuratum_web/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package accuratum-web --no-editable

# --- runtime ---------------------------------------------------------------
FROM python:3.11-slim-bookworm AS runtime

# MPLCONFIGDIR: matplotlib's font cache is built here at build time, so no
# instance spends its cold start on it.
ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    MPLCONFIGDIR=/opt/matplotlib

COPY --from=build /app/.venv /app/.venv
RUN python -c "import matplotlib.font_manager" \
    && chmod -R a+rX /opt/matplotlib

# A user without privileges: the route is public and unauthenticated. Its
# home is writable for whatever astropy or fontconfig want to put there.
RUN useradd --create-home --uid 1000 accuratum
USER accuratum
WORKDIR /home/accuratum

# Cloud Run injects PORT=8080 and ignores EXPOSE; locally it's 8000.
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", \
         "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/api/health').read(1)"]

# Shell form because exec form doesn't expand ${PORT}; `exec` keeps uvicorn as
# PID 1 so it gets Cloud Run's SIGTERM. One uvicorn worker: the rate limit
# and the computation cap live in its memory, and the half-years run in its
# own process pool. The client IP comes from headers in app.py (_client).
CMD ["sh", "-c", \
     "exec uvicorn accuratum_web.app:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
