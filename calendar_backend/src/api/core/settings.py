import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Load environment variables from .env if present (container will provide them).
load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    secret_key: str
    access_token_exp_minutes: int
    cors_allow_origins: list[str]
    data_dir: str


def _parse_csv(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """Return strongly-typed settings for the application."""
    secret = os.getenv("SECRET_KEY", "dev-secret-change-me")
    exp = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
    cors = os.getenv("CORS_ALLOW_ORIGINS", "*")
    data_dir = os.getenv("DATA_DIR", "data")
    return Settings(
        secret_key=secret,
        access_token_exp_minutes=exp,
        cors_allow_origins=["*"] if cors.strip() == "*" else _parse_csv(cors),
        data_dir=data_dir,
    )
