from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DEBUG: bool = True
    PLATFORM: str = "testmaker.app"
    APP_NAME: str = "TestMaker"
    APP_PREFIX: str = "Test"
    APP_SUFFIX: str = "Maker"
    APP_VERSION: str = "0.1.0"
    APP_URL: str = "https://examtopics.app"
    APP_DESCRIPTION: str = "Free IT certification practice questions for AWS, Azure, GCP, CompTIA and more."
    DATABASE_URL: str = "sqlite:///./testmaker.db"
    SECRET_KEY: str = "change-me-in-production"
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"

    DOCS_USERNAME: str
    DOCS_PASSWORD: str
    
    OPENROUTER_API_KEY: str = ""
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    class Config:
        env_file = ".env"


settings = Settings()
