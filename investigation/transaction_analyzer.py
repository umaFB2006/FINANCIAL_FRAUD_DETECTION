"""Analyze a transaction in the context of user history."""

from ml.behaviour_profiler import build_profile


def analyze(txn, history):
    profile = build_profile(history)
    return {
        "history_count": profile["count"],
        "typical_amount": profile["median_amount"],
        "common_location": profile["common_location"],
        "common_device": profile["common_device"],
        "common_beneficiary": profile["common_beneficiary"],
        "amount": txn.get("amount"),
        "location": txn.get("location"),
        "device_id": txn.get("device_id"),
        "beneficiary": txn.get("beneficiary"),
        "risk_score": txn.get("risk_score"),
        "risk_level": txn.get("risk_level"),
    }
