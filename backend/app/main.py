from fastapi import FastAPI

app = FastAPI(
    title="Quran AI Platform API",
    description="Backend API for the Quran AI learning platform.",
    version="0.1.0",
)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    """Return the API health status."""
    return {"status": "ok"}
