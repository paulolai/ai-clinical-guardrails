from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pwa.backend.config import settings
from pwa.backend.routes import recordings

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(recordings.router)


@app.get("/api/v1/health")
async def health_check() -> dict[str, str | dict[str, str]]:
    return {"status": "healthy", "components": {"pwa": "ok"}}
