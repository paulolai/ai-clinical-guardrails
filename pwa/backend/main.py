from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from pwa.backend.config import settings
from pwa.backend.database import get_db
from pwa.backend.models.recording import RecordingStatus
from pwa.backend.routes import pages, recordings
from pwa.backend.services.recording_service import RecordingService

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


@app.on_event("startup")
async def recover_zombie_jobs() -> None:
    """Mark stuck jobs as failed on startup."""
    async for db in get_db():
        service = RecordingService(db)
        # Find recordings stuck in PROCESSING for > 30 minutes
        stuck = await service.get_recordings_stuck_in_processing(minutes=30)
        for recording in stuck:
            await service.update_recording_status(
                recording.id,
                RecordingStatus.ERROR,
                error_message="Job lost due to server restart",
            )
            print(f"[Recovery] Marked zombie job {recording.id} as failed")
