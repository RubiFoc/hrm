"""Application entrypoint and API wiring for the HRM backend service."""

from fastapi import FastAPI

app = FastAPI(title="HRM Backend", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Return a lightweight service health response.

    Returns:
        dict[str, str]: Static health status payload used by monitoring checks.
    """
    return {"status": "ok"}
