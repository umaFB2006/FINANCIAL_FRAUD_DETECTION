"""Human-readable reasons for a risk score. Optional SHAP if installed."""

from utils.logger import get_logger

logger = get_logger(__name__)


def explain_transaction(feature_row, rule_hits, ml_probability, anomaly):
    reasons = []
    amount_dev = float(feature_row.get("amount_deviation") or 0)
    if amount_dev >= 2:
        reasons.append("Transaction amount is significantly higher than customer average")
    elif amount_dev >= 1:
        reasons.append("Transaction amount differs from typical customer spend")

    if feature_row.get("unusual_device"):
        reasons.append("New or unusual device detected")
    if feature_row.get("unusual_location"):
        reasons.append("Unusual transaction location for this customer")
    if int(feature_row.get("is_international") or 0) == 1:
        reasons.append("International transaction")
    if float(feature_row.get("velocity_count") or 0) >= 4:
        reasons.append("Multiple transactions detected within a short time")
    if float(feature_row.get("balance_ratio") or 0) >= 0.5:
        reasons.append("Amount is a large share of the available account balance")
    if float(feature_row.get("hour") or 12) in (0, 1, 2, 3, 4):
        reasons.append("Transaction occurred during unusual hours")

    for hit in rule_hits or []:
        if hit["message"] not in reasons:
            reasons.append(hit["message"])

    if ml_probability >= 0.6:
        reasons.append("Supervised fraud model assigned a high fraud probability")
    if anomaly >= 70:
        reasons.append("Anomaly detector flagged atypical behaviour")

    if not reasons:
        reasons.append("No strong fraud indicators; treated as routine activity")

    shap_note = None
    try:
        import shap  # noqa: F401

        shap_note = "SHAP is installed; rule and feature contributions are used for the live demo."
    except Exception:
        shap_note = "SHAP unavailable; explanations use feature contributions and rules."

    return {
        "top_reasons": reasons[:6],
        "feature_snapshot": {
            "amount_deviation": round(amount_dev, 3),
            "velocity_count": feature_row.get("velocity_count"),
            "unusual_device": feature_row.get("unusual_device"),
            "unusual_location": feature_row.get("unusual_location"),
            "is_international": feature_row.get("is_international"),
            "ml_probability": round(float(ml_probability), 4),
            "anomaly_score": anomaly,
        },
        "method": shap_note,
    }
