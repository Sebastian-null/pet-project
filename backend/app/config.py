from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://briefs:briefs_dev_password@localhost:5432/briefs"
    jwt_secret: str = "replace-this-before-production"
    jwt_algorithm: str = "HS256"
    environment: str = "development"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "BRIEFS <no-reply@briefs.local>"
    storefront_url: str = "http://localhost:3000"
    media_dir: str = "media"
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_currency: str = "uah"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
