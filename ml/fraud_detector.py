"""Load the trained classifier and return ML fraud scores."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np

from config import Config
from ml.preprocessing import features_to_row, transaction_to_features


class FraudDetector:
    def __init__(self, model_path=None, preprocessor_path=None):
        self.model_path = Path(model_path or Config.MODEL_PATH)
        self.preprocessor_path = Path(preprocessor_path or Config.PREPROCESSOR_PATH)
        self.model = None
        self.preprocessor = None
        self._load()

    def _load(self):
        if self.model_path.exists() and self.preprocessor_path.exists():
            self.model = joblib.load(self.model_path)
            loaded = joblib.load(self.preprocessor_path)
            if hasattr(loaded, "transform"):
                self.preprocessor = loaded
            elif isinstance(loaded, dict) and "scaler" in loaded:
                self.preprocessor = loaded["scaler"]
            else:
                self.preprocessor = loaded

    @property
    def is_ready(self):
        return self.model is not None and self.preprocessor is not None

    def predict(self, txn):
        features = transaction_to_features(txn)
        if not self.is_ready:
            return self._heuristic(features)

        row = np.array([features_to_row(features)], dtype=float)
        transformed = self.preprocessor.transform(row)
        proba_all = self.model.predict_proba(transformed)[0]
        classes = list(getattr(self.model, "classes_", [0, 1]))
        if 1 in classes:
            proba = float(proba_all[classes.index(1)])
        else:
            proba = float(proba_all[-1])
        prediction = "FRAUD" if proba >= 0.5 else "LEGITIMATE"
        return {
            "prediction": prediction,
            "fraud_probability": round(proba, 4),
            "ml_score": round(max(0.0, min(100.0, proba * 100.0)), 2),
            "features": features,
        }

    def _heuristic(self, features):
        score = 0.0
        score += min(40.0, features["amount"] / 4000.0)
        score += 18.0 * features["is_international"]
        score += 14.0 * features["is_new_device"]
        score += 14.0 * features["is_new_beneficiary"]
        score += 16.0 * features["is_night"]
        score = max(0.0, min(100.0, score))
        proba = score / 100.0
        return {
            "prediction": "FRAUD" if proba >= 0.5 else "LEGITIMATE",
            "fraud_probability": round(proba, 4),
            "ml_score": round(score, 2),
            "features": features,
        }


_detector = None


def get_detector():
    global _detector
    if _detector is None:
        _detector = FraudDetector()
    return _detector


def reset_detector():
    global _detector
    _detector = None
