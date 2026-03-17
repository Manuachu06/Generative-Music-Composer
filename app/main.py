from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import settings

app = FastAPI(title=settings.app_name)
app.include_router(router)

frontend_dir = Path(__file__).parent / "frontend"
media_dir = Path(__file__).parent / "media"
media_dir.mkdir(parents=True, exist_ok=True)

app.mount("/frontend", StaticFiles(directory=frontend_dir), name="frontend")
app.mount("/media", StaticFiles(directory=media_dir), name="media")


@app.get("/")
def frontend() -> FileResponse:
    return FileResponse(frontend_dir / "index.html")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "env": settings.environment}
