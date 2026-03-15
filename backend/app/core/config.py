from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    project_name: str = "CRM AZS"
    backend_cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000", "*"]

    # DB — переменные для Docker (POSTGRES_USER, POSTGRES_PASSWORD и т.д.)
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "crm_user"
    postgres_password: str = "crm_pass"
    postgres_db: str = "crm_azs"

    # SMTP (опционально, для email-уведомлений)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    frontend_url: str = ""  # для ссылки сброса пароля, например https://crm.example.com

    # Security
    secret_key: str = "CHANGE_ME_SECRET_KEY"
    access_token_expire_minutes: int = 60 * 8
    algorithm: str = "HS256"

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def sqlalchemy_database_uri(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:"
            f"{self.postgres_password}@{self.postgres_host}:"
            f"{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
