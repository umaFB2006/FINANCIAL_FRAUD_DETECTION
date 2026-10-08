"""Orchestrate ML, anomaly detection, rules, and risk scoring."""

from fraud_detection.risk_engine import combine_scores
from fraud_detection.rule_engine import evaluate_rules
from ml.anomaly_detection import anomaly_score
from ml.explainability import explain_transaction
from ml.feature_engineering import features_from_context
from ml.predict import predict_transaction
from services.ibm_integration import optional_ibm_score
from utils.logger import get_logger

logger = get_logger(__name__)


def detect(txn, history_rows):
    features = features_from_context(txn, history_rows)
    ml = predict_transaction(features)
    anomaly = anomaly_score(features)
    rules = evaluate_rules(features, txn)
    ibm = optional_ibm_score(features)
    ml_prob = ml["fraud_probability"]
    if ibm.get("used"):
        ml_prob = (ml_prob + ibm["probability"]) / 2

    combined = combine_scores(ml_prob, anomaly, rules["rule_score"])
    explanation = explain_transaction(features, rules["triggered_rules"], ml_prob, anomaly)

    result = {
        "prediction": combined["prediction"],
        "fraud_probability": round(ml_prob, 4),
        "risk_score": combined["risk_score"],
        "severity": combined["severity"],
        "model_name": ml.get("model_name"),
        "components": combined["components"],
        "rules": rules,
        "explanation": explanation,
        "features": features,
        "ibm": ibm,
        "disclaimer": "AI-based risk prediction, not a confirmed fraud decision.",
    }
    logger.info(
        "Detection txn=%s prediction=%s risk=%s",
        txn.get("transaction_id"),
        result["prediction"],
        result["risk_score"],
    )
    return result
