from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class PWASettings(BaseSettings):
    model_config = ConfigDict(env_prefix="PWA_")

    app_name: str = "Clinical Transcription PWA"
    debug: bool = False
    database_url: str = "sqlite+aiosqlite:///./data/clinical.db"


settings = PWASettings()
