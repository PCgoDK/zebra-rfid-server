"""ASGI entrypoint."""

from fastapi import FastAPI

from app.config import get_settings


settings = get_settings()
app = FastAPI(title="Zebra RFID Server")


@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "application": settings.app_name}
