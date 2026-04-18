from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
    )
    DEBUG: bool = True
    PLATFORM: str = "freeitexam.com"
    APP_NAME: str = "FreeITExam"
    APP_PREFIX: str
    APP_SUFFIX: str
    APP_VERSION: str = "0.1.0"
    APP_URL: str = "https://freeitexam.com"
    BACKEND_ALGOHOLIC_URL: str
    APP_DESCRIPTION: str = "Free IT certification practice questions for AWS, Azure, GCP, CompTIA and more."
    DATABASE_URL: str = "sqlite:///./freeitexam.db"
    SECRET_KEY: str = "change-me-in-production"
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"
    QUESTIONS_PER_TEST: int = Field(default=5)

    DOCS_USERNAME: str
    DOCS_PASSWORD: str
    
    OPENROUTER_API_KEY: str = ""
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"


settings = Settings()

