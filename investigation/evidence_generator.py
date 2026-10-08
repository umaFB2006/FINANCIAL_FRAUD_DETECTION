"""Create structured evidence records for suspicious indicators."""

from ml.preprocessing import parse_hour, to_int_flag
from database.db import execute, utcnow_iso


def build_evidence_items(txn, ml_result, behavior_reasons):
    items = []
    amount = float(txn.get("amount") or 0)
    if amount >= 20000:
        items.append(
            (
                "HIGH_AMOUNT_DEVIATION",
                f"Amount ₹{amount:,.2f} is high relative to typical retail activity.",
                "HIGH" if amount >= 100000 else "MEDIUM",
                "RULE_ENGINE",
            )
        )
    if to_int_flag(txn.get("is_new_device")):
        items.append(("NEW_DEVICE", "Transaction originated from a new device.", "HIGH", "BEHAVIOR"))
    if to_int_flag(txn.get("is_new_beneficiary")):
        items.append(("NEW_BENEFICIARY", "Funds directed to a new beneficiary.", "HIGH", "BEHAVIOR"))
    location = txn.get("location")
    items.append(
        (
            "UNUSUAL_LOCATION",
            f"Transaction location recorded as {location}.",
            "MEDIUM",
            "BEHAVIOR",
        )
    )
    hour = parse_hour(txn.get("transaction_time"))
    if hour < 6 or hour >= 23:
        items.append(
            ("UNUSUAL_TIME", f"Transaction time hour {hour:02d} is outside normal hours.", "HIGH", "RULE_ENGINE")
        )
    if to_int_flag(txn.get("is_international")):
        items.append(
            ("INTERNATIONAL_TRANSACTION", "International transfer flag is set.", "HIGH", "RULE_ENGINE")
        )
    if float(ml_result.get("ml_score") or 0) >= 60:
        items.append(
            (
                "ML_FRAUD_SIGNAL",
                f"Classifier fraud probability {ml_result.get('fraud_probability')}.",
                "HIGH",
                "ML_MODEL",
            )
        )
    status = str(txn.get("status") or "")
    if "FAIL" in status.upper():
        items.append(
            ("FAILED_TRANSACTION_PATTERN", "Failed or blocked status pattern observed.", "MEDIUM", "ANALYZER")
        )
    if len(behavior_reasons) >= 3:
        items.append(
            ("HIGH_FREQUENCY", "Multiple simultaneous behavior anomalies were detected.", "MEDIUM", "BEHAVIOR")
        )
    return items


def persist_evidence(investigation_id, items):
    for evidence_type, description, severity, source in items:
        execute(
            """
            INSERT INTO evidence (investigation_id, evidence_type, description, severity, source, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (investigation_id, evidence_type, description, severity, source, utcnow_iso()),
        )
