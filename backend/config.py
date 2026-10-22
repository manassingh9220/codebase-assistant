from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    codebase_db_url : str
    voyage_api_key : str = ""
    # Free tier (no payment method) allows 10K tokens/minute; raise it after adding billing
    voyage_tokens_per_minute : int = 10_000
    github_token : str = ""
    app_env : str = "development"
    app_port : int = 8000
    embedding_dim : int = 1024

settings = Settings()