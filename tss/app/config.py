from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://tss:tss@localhost:5432/tss"
    ENV: str = "development"
    LOG_LEVEL: str = "INFO"


settings = Settings()
