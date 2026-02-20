"""
Configuration — Central settings for the backend.
"""
import os

APP_ENV = os.getenv("APP_ENV", "development").lower()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if APP_ENV in ("production", "prod"):
        raise ValueError("SECRET_KEY is required in production")
    SECRET_KEY = "cricket-dev-key-2026"

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cricket.db")

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")


def parse_cors_origins(raw: str) -> list[str]:
    if not raw or raw.strip() == "*":
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


CORS_ORIGINS_LIST = parse_cors_origins(CORS_ORIGINS)
