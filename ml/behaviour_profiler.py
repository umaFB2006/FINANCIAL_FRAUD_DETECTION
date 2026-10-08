"""User behavior profiling from SQLite history (no ML retraining)."""

from __future__ import annotations

from collections import Counter
from statistics import median

from ml.preprocessing import parse_hour, to_int_flag


def _most_common(values, default="UNKNOWN"):
    cleaned = [v for v in values if v not in (None, "")]
    if not cleaned:
        return default
    return Counter(cleaned).most_common(1)[0][0]


def build_profile(history_rows):
    if not history_rows:
        return {
            "count": 0,
            "average_amount": 0.0,
            "median_amount": 0.0,
            "min_amount": 0.0,
            "max_amount": 0.0,
            "normal_amount_low": 0.0,
            "normal_amount_high": 0.0,
            "common_location": None,
            "common_device": None,
            "common_beneficiary": None,
            "common_transaction_type": None,
            "common_hour": None,
            "transaction_frequency": 0,
            "international_percentage": 0.0,
            "new_device_percentage": 0.0,
            "new_beneficiary_percentage": 0.0,
            "has_history": False,
        }

    amounts = [float(r["amount"]) for r in history_rows]
    hours = [parse_hour(r.get("transaction_time")) for r in history_rows]
    avg = sum(amounts) / len(amounts)
    med = float(median(amounts))
    mn = min(amounts)
    mx = max(amounts)
    spread = max(mx - mn, med * 0.5, 200.0)

    intl = [to_int_flag(r.get("is_international")) for r in history_rows]
    new_dev = [to_int_flag(r.get("is_new_device")) for r in history_rows]
    new_ben = [to_int_flag(r.get("is_new_beneficiary")) for r in history_rows]

    return {
        "count": len(history_rows),
        "average_amount": round(avg, 2),
        "median_amount": round(med, 2),
        "min_amount": round(mn, 2),
        "max_amount": round(mx, 2),
        "normal_amount_low": round(max(0.0, med - spread), 2),
        "normal_amount_high": round(med + spread, 2),
        "common_location": _most_common([r.get("location") for r in history_rows]),
        "common_device": _most_common([r.get("device_id") for r in history_rows]),
        "common_beneficiary": _most_common([r.get("beneficiary") for r in history_rows]),
        "common_transaction_type": _most_common(
            [r.get("transaction_type") for r in history_rows]
        ),
        "common_hour": _most_common(hours, default=12),
        "transaction_frequency": len(history_rows),
        "international_percentage": round(100.0 * sum(intl) / len(intl), 2),
        "new_device_percentage": round(100.0 * sum(new_dev) / len(new_dev), 2),
        "new_beneficiary_percentage": round(100.0 * sum(new_ben) / len(new_ben), 2),
        "has_history": True,
    }


def calculate_behavior_score(txn, profile):
    """Score 0-100 based on deviation from prior user behavior."""
    amount = float(txn.get("amount") or 0)
    hour = parse_hour(txn.get("transaction_time"))
    reasons = []
    score = 0.0

    if not profile.get("has_history"):
        if amount >= 100000:
            score += 35
            reasons.append("High amount with no prior transaction baseline.")
        elif amount >= 20000:
            score += 18
            reasons.append("Elevated amount with limited user history.")
        if to_int_flag(txn.get("is_international")):
            score += 20
            reasons.append("International transaction on a new or sparse profile.")
        if to_int_flag(txn.get("is_new_device")):
            score += 15
            reasons.append("New device used without historical device baseline.")
        if to_int_flag(txn.get("is_new_beneficiary")):
            score += 15
            reasons.append("New beneficiary used without historical baseline.")
        if hour < 6 or hour >= 23:
            score += 15
            reasons.append("Transaction occurred at an unusual time.")
        return round(max(0.0, min(100.0, score)), 2), reasons

    typical = max(profile["median_amount"], profile["average_amount"], 1.0)
    if amount > typical * 8:
        score += 40
        reasons.append("Transaction amount is significantly higher than the user's normal amount.")
    elif amount > typical * 3:
        score += 25
        reasons.append("Transaction amount is well above the user's typical range.")
    elif amount > profile["normal_amount_high"]:
        score += 12
        reasons.append("Transaction amount is outside the user's normal amount range.")

    location = str(txn.get("location") or "").strip()
    if profile["common_location"] and location and location.lower() != str(profile["common_location"]).lower():
        score += 12
        reasons.append("Location differs from the user's common transaction location.")

    device = str(txn.get("device_id") or "").strip()
    if to_int_flag(txn.get("is_new_device")) or (
        profile["common_device"] and device and device != profile["common_device"]
    ):
        score += 14
        reasons.append("New or uncommon device detected.")

    beneficiary = str(txn.get("beneficiary") or "").strip()
    if to_int_flag(txn.get("is_new_beneficiary")) or (
        profile["common_beneficiary"]
        and beneficiary
        and beneficiary.lower() != str(profile["common_beneficiary"]).lower()
    ):
        score += 14
        reasons.append("New or uncommon beneficiary detected.")

    txn_type = str(txn.get("transaction_type") or "").strip().upper()
    if (
        profile["common_transaction_type"]
        and txn_type
        and txn_type != str(profile["common_transaction_type"]).upper()
    ):
        score += 8
        reasons.append("Unusual transaction type compared with user history.")

    common_hour = profile.get("common_hour")
    if hour < 6 or hour >= 23:
        score += 16
        reasons.append("Transaction occurred at an unusual time.")
    elif common_hour is not None and abs(int(common_hour) - hour) >= 8:
        score += 8
        reasons.append("Transaction hour differs from the user's typical activity window.")

    if to_int_flag(txn.get("is_international")) and profile["international_percentage"] < 20:
        score += 16
        reasons.append("International transaction is unusual for this user.")

    if profile["count"] >= 3:
        recent_window = min(profile["count"], 8)
        if recent_window >= 6:
            score += 6
            reasons.append("Transaction frequency is elevated relative to a typical session.")

    return round(max(0.0, min(100.0, score)), 2), reasons
