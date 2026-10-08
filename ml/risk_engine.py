"""Rule scoring and hybrid risk engine."""

from __future__ import annotations

from config import Config
from ml.preprocessing import parse_hour, to_int_flag


def calculate_rule_score(txn):
    score = 0.0
    amount = float(txn.get("amount") or 0)
    if amount >= 100000:
        score += 40
    elif amount >= 50000:
        score += 28
    elif amount >= 20000:
        score += 18
    elif amount >= 10000:
        score += 10

    if to_int_flag(txn.get("is_international")):
        score += 18
    if to_int_flag(txn.get("is_new_device")):
        score += 14
    if to_int_flag(txn.get("is_new_beneficiary")):
        score += 14

    hour = parse_hour(txn.get("transaction_time"))
    if hour < 6 or hour >= 23:
        score += 16

    txn_type = str(txn.get("transaction_type") or "").upper()
    if txn_type in {"TRANSFER", "WITHDRAWAL"} and amount >= 50000:
        score += 8

    return round(max(0.0, min(100.0, score)), 2)


def classify_risk(risk_score):
    score = max(0.0, min(100.0, float(risk_score)))
    if score <= Config.RISK_LOW_MAX:
        return "LOW", "AUTO_APPROVED"
    if score <= Config.RISK_MEDIUM_MAX:
        return "MEDIUM", "ADDITIONAL_VERIFICATION"
    return "HIGH", "UNDER_INVESTIGATION"


def calculate_final_risk(ml_score, rule_score, behavior_score):
    risk = (
        float(ml_score) * Config.ML_WEIGHT
        + float(rule_score) * Config.RULE_WEIGHT
        + float(behavior_score) * Config.BEHAVIOR_WEIGHT
    )
    risk = max(0.0, min(100.0, risk))
    level, action = classify_risk(risk)
    return round(risk, 2), level, action
