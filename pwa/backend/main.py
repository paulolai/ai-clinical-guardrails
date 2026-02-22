from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from pwa.backend.config import settings
from pwa.backend.routes import pages, recordings

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files using absolute path from project root
STATIC_DIR = Path(__file__).parent.parent / "frontend" / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Include routes
app.include_router(recordings.router)
app.include_router(pages.router)


@app.get("/api/v1/health")
async def health_check() -> dict[str, str | dict[str, str]]:
    return {"status": "healthy", "components": {"pwa": "ok"}}
