import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


class BaseConfig:
    APP_NAME = "Escala de Serviço"
    APP_VERSION = "v0.7"
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOG_DIR = BASE_DIR / "logs"
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_MAX_BYTES = 1_000_000
    LOG_BACKUP_COUNT = 3
    HOST = os.environ.get("FLASK_RUN_HOST", "127.0.0.1")
    PORT = int(os.environ.get("FLASK_RUN_PORT", "5000"))


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = (
        "sqlite:///" + str(BASE_DIR / "instance" / "escala.db")
    )


class TestingConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class LocalProductionConfig(BaseConfig):
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = (
        "sqlite:///" + str(BASE_DIR / "instance" / "escala.db")
    )


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": LocalProductionConfig,
}
