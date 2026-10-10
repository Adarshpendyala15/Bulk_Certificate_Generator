from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./certificates.db"
    CERTIFICATES_DIR: str = "./generated_certificates"
    PROCESSING_MODE: str = "async"
    MAX_RECIPIENTS_PER_JOB: int = 1000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
