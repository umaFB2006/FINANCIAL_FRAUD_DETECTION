"""Application configuration. SECRET_KEY is read from the environment."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-local-secret-change-me")
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024

    DATABASE_PATH = os.environ.get(
        "DATABASE_PATH",
        str(BASE_DIR / "database" / "fraud_detection.db"),
    )
    MODEL_PATH = BASE_DIR / "models" / "fraud_model.pkl"
    PREPROCESSOR_PATH = BASE_DIR / "models" / "preprocessor.pkl"
    DATA_CSV_PATH = BASE_DIR / "data" / "transactions.csv"
    REPORTS_DIR = BASE_DIR / "generated_reports"

    ML_WEIGHT = 0.50
    RULE_WEIGHT = 0.30
    BEHAVIOR_WEIGHT = 0.20

    RISK_LOW_MAX = 30
    RISK_MEDIUM_MAX = 70

    OTP_EXPIRY_SECONDS = 120
    OTP_DEMO_MODE = True


def get_database_path(override=None):
    if override:
        return str(override)
    return os.environ.get(
        "DATABASE_PATH",
        str(BASE_DIR / "database" / "fraud_detection.db"),
    )
