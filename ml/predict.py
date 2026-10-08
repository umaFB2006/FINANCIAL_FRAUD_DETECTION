"""Load persisted models and score a single feature row."""

import joblib
import numpy as np

from config import Config
from utils.constants import NUMERIC_FEATURES
from utils.logger import get_logger

logger = get_logger(__name__)

_CACHE = {}


def _load(path, key):
    if key in _CACHE:
        return _CACHE[key]
    if not path.exists():
        return None
    obj = joblib.load(path)
    _CACHE[key] = obj
    return obj


def models_available():
    return Config.FRAUD_MODEL_PATH.exists() and Config.SCALER_PATH.exists()


def feature_vector(feature_row):
    columns = _load(Config.FEATURE_COLUMNS_PATH, "columns") or NUMERIC_FEATURES
    return np.array([[float(feature_row.get(col, 0) or 0) for col in columns]], dtype=float)


def predict_transaction(feature_row):
    """Return ML probability using the saved classifier. Never retrains."""
    model = _load(Config.FRAUD_MODEL_PATH, "model")
    scaler = _load(Config.SCALER_PATH, "scaler")
    meta = _load(Config.MODEL_META_PATH, "meta") or {"name": "unavailable"}
    if model is None or scaler is None:
        logger.warning("Fraud model not found; returning rule-only probability placeholder")
        amount_dev = float(feature_row.get("amount_deviation") or 0)
        velocity = float(feature_row.get("velocity_count") or 0)
        heuristic = min(0.99, 0.15 * amount_dev + 0.08 * max(velocity - 1, 0))
        return {
            "fraud_probability": heuristic,
            "risk_score": round(heuristic * 100, 2),
            "prediction": "FRAUD" if heuristic >= 0.6 else "SUSPICIOUS" if heuristic >= 0.3 else "NORMAL",
            "model_name": "heuristic_fallback",
        }

    x = scaler.transform(feature_vector(feature_row))
    if hasattr(model, "predict_proba"):
        proba = float(model.predict_proba(x)[0, 1])
    else:
        proba = float(model.predict(x)[0])
    score = round(proba * 100, 2)
    label = "FRAUD" if score >= Config.FRAUD_THRESHOLD else "SUSPICIOUS" if score >= 30 else "NORMAL"
    return {
        "fraud_probability": round(proba, 4),
        "risk_score": score,
        "prediction": label,
        "model_name": meta.get("name", "saved_model"),
    }
