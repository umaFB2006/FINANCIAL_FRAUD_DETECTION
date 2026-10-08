"""Isolation Forest anomaly scoring with a 0-100 mapping."""

import joblib
import numpy as np

from config import Config
from ml.predict import feature_vector
from utils.logger import get_logger

logger = get_logger(__name__)
_ISO = None


def _iso():
    global _ISO
    if _ISO is not None:
        return _ISO
    if not Config.ANOMALY_MODEL_PATH.exists():
        return None
    _ISO = joblib.load(Config.ANOMALY_MODEL_PATH)
    return _ISO


def anomaly_score(feature_row):
    model = _iso()
    scaler_path = Config.SCALER_PATH
    if model is None or not scaler_path.exists():
        # Heuristic fallback when the anomaly model is not trained yet.
        flags = (
            float(feature_row.get("amount_deviation") or 0)
            + float(feature_row.get("unusual_device") or 0)
            + float(feature_row.get("unusual_location") or 0)
            + max(float(feature_row.get("velocity_count") or 1) - 2, 0)
        )
        return round(min(100.0, flags * 18), 2)

    import joblib as jb

    scaler = jb.load(scaler_path)
    x = scaler.transform(feature_vector(feature_row))
    raw = float(model.decision_function(x)[0])
    # IsolationForest: lower (more negative) scores are more anomalous.
    mapped = 1 / (1 + np.exp(raw * 3))
    return round(float(mapped) * 100, 2)
