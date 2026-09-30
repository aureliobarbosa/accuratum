"""The FastAPI app: the sundial API and the static page."""

from fastapi import FastAPI

app = FastAPI(title="Accuratum", docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
