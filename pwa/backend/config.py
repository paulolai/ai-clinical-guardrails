from pydantic_settings import BaseSettings


class PWASettings(BaseSettings):  # type: ignore[misc]
    app_name: str = "Clinical Transcription PWA"
    debug: bool = False
    database_url: str = "sqlite+aiosqlite:///./data/clinical.db"

    class Config:
        env_prefix = "PWA_"


settings = PWASettings()
