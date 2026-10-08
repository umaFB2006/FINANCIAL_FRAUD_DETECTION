"""Combine ML, anomaly, and rule scores into a risk result."""

from config import Config
from utils.helpers import classification_from_score, severity_from_score


def combine_scores(ml_probability, anomaly, rule_score):
    ml_part = float(ml_probability) * 100
    risk = (
        Config.ML_WEIGHT * ml_part
        + Config.ANOMALY_WEIGHT * float(anomaly)
        + Config.RULE_WEIGHT * float(rule_score)
    )
    risk = max(0.0, min(100.0, risk))
    return {
        "risk_score": round(risk, 2),
        "severity": severity_from_score(risk),
        "prediction": classification_from_score(risk),
        "components": {
            "ml": round(ml_part, 2),
            "anomaly": round(float(anomaly), 2),
            "rules": round(float(rule_score), 2),
        },
    }
