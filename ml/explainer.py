"""Human-readable explanations for a scored transaction."""

from __future__ import annotations

from ml.preprocessing import parse_hour, to_int_flag


def explain_transaction(txn, ml_result, rule_score, behavior_score, behavior_reasons, profile):
    reasons = []
    ml_score = float(ml_result.get("ml_score") or 0)

    if ml_score >= 70:
        reasons.append("ML model detected high fraud probability.")
    elif ml_score >= 40:
        reasons.append("ML model detected elevated fraud probability.")
    else:
        reasons.append("ML model assessed a low fraud probability.")

    amount = float(txn.get("amount") or 0)
    if amount >= 100000:
        reasons.append("Rule engine flagged a very high transaction amount.")
    elif amount >= 20000:
        reasons.append("Rule engine noted an elevated transaction amount.")

    if to_int_flag(txn.get("is_international")):
        reasons.append("International transaction detected.")
    if to_int_flag(txn.get("is_new_device")):
        reasons.append("New device detected.")
    if to_int_flag(txn.get("is_new_beneficiary")):
        reasons.append("New beneficiary detected.")

    hour = parse_hour(txn.get("transaction_time"))
    if hour < 6 or hour >= 23:
        reasons.append("Transaction occurred at an unusual time.")

    for item in behavior_reasons:
        if item not in reasons:
            reasons.append(item)

    if profile.get("has_history"):
        reasons.append(
            f"Compared against {profile['count']} prior transaction(s); "
            f"typical amount about ₹{profile['median_amount']:,.2f}."
        )
    else:
        reasons.append("No prior history was available; baseline rules and ML were used.")

    # Feature importance fallback (no SHAP required).
    feature_weights = [
        ("amount", amount / 2000.0),
        ("international", 18 if to_int_flag(txn.get("is_international")) else 0),
        ("new_device", 14 if to_int_flag(txn.get("is_new_device")) else 0),
        ("new_beneficiary", 14 if to_int_flag(txn.get("is_new_beneficiary")) else 0),
        ("night", 16 if hour < 6 or hour >= 23 else 0),
    ]
    feature_weights.sort(key=lambda x: x[1], reverse=True)
    top = [name for name, weight in feature_weights if weight > 0][:4]
    if top:
        reasons.append("Top contributing signals: " + ", ".join(top) + ".")

    unique = []
    for reason in reasons:
        if reason not in unique:
            unique.append(reason)
    return unique
