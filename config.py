import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)

DEFAULT_SQLITE_PATH = os.path.join(INSTANCE_DIR, "college_erp.db")
DEFAULT_SQLITE_URI = f"sqlite:///{DEFAULT_SQLITE_PATH}"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-in-production")

    # SQLite by default — a single file, zero setup, nothing to install.
    # Override DATABASE_URL if you ever want to point this at MySQL/Postgres
    # instead (e.g. mysql+pymysql://user:pass@host/dbname).
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", DEFAULT_SQLITE_URI)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = (
        {"connect_args": {"check_same_thread": False}}
        if SQLALCHEMY_DATABASE_URI.startswith("sqlite")
        else {}
    )

    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    WTF_CSRF_ENABLED = True
