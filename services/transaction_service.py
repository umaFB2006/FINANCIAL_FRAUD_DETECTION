"""Persist transactions and run the full detection pipeline."""

from datetime import datetime

from database.database import execute, get_connection, query_all, query_one
from fraud_detection.detector import detect
from investigation.investigator import maybe_investigate
from services.alert_service import maybe_create_alert
from services.notification_service import notify_critical
from utils.logger import get_logger

logger = get_logger(__name__)


def next_transaction_id():
    row = query_one(
        "SELECT transaction_id FROM transactions ORDER BY transaction_id DESC LIMIT 1"
    )
    if not row:
        return "TXN10001"
    digits = "".join(ch for ch in row["transaction_id"] if ch.isdigit())
    return f"TXN{int(digits) + 1}"


def customer_history(customer_id, limit=40):
    return query_all(
        """
        SELECT * FROM transactions
        WHERE customer_id = ?
        ORDER BY transaction_time DESC
        LIMIT ?
        """,
        (customer_id, limit),
    )


def store_transaction(payload):
    txn_id = payload.get("transaction_id") or next_transaction_id()
    now = payload.get("transaction_time") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    intl = payload.get("is_international", False)
    if isinstance(intl, str):
        intl = 1 if intl.lower() in ("true", "1") else 0
    intl = int(bool(intl))
    execute(
        """
        INSERT INTO transactions (
            transaction_id, customer_id, transaction_amount, transaction_type,
            transaction_time, merchant, location, device_id, ip_address,
            payment_method, account_balance, transaction_frequency, is_international
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            txn_id,
            payload["customer_id"],
            float(payload["amount"]),
            str(payload["transaction_type"]).upper(),
            now,
            payload["merchant"],
            payload["location"],
            payload["device_id"],
            payload["ip_address"],
            str(payload["payment_method"]).upper(),
            float(payload["account_balance"]),
            int(payload.get("transaction_frequency") or 0),
            intl,
        ),
    )
    payload["transaction_id"] = txn_id
    payload["transaction_time"] = now
    payload["amount"] = float(payload["amount"])
    payload["is_international"] = intl
    return payload


def save_prediction(transaction_id, detection):
    execute(
        """
        INSERT INTO fraud_predictions (
            transaction_id, fraud_probability, risk_score, prediction, model_name
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            transaction_id,
            detection["fraud_probability"],
            detection["risk_score"],
            detection["prediction"],
            detection.get("model_name"),
        ),
    )


def process_transaction(payload):
    customer = query_one("SELECT * FROM customers WHERE customer_id = ?", (payload.get("customer_id"),))
    if not customer:
        raise ValueError(f"Unknown customer_id: {payload.get('customer_id')}")
    history = customer_history(payload["customer_id"])
    stored = store_transaction(payload)
    detection = detect(stored, history)
    save_prediction(stored["transaction_id"], detection)
    alert_id = maybe_create_alert(stored["transaction_id"], detection)
    stored["alert_id"] = alert_id
    investigation = None
    if alert_id:
        investigation = maybe_investigate(stored, detection, history)
    if detection.get("severity") == "CRITICAL":
        notify_critical(
            alert_id,
            stored["transaction_id"],
            detection["risk_score"],
            detection.get("explanation", {}).get("top_reasons"),
        )
    return {
        "transaction": stored,
        "customer": customer,
        "detection": detection,
        "alert_id": alert_id,
        "investigation": investigation,
    }


def process_existing_transactions(db_path=None, limit=None):
    """Score seeded transactions that do not yet have predictions."""
    conn = get_connection(db_path)
    try:
        sql = """
            SELECT t.* FROM transactions t
            LEFT JOIN fraud_predictions p ON p.transaction_id = t.transaction_id
            WHERE p.prediction_id IS NULL
            ORDER BY t.transaction_time ASC
        """
        rows = [dict(r) for r in conn.execute(sql).fetchall()]
    finally:
        conn.close()
    if limit:
        rows = rows[:limit]
    logger.info("Scoring %s existing transactions", len(rows))
    for row in rows:
        payload = {
            "transaction_id": row["transaction_id"],
            "customer_id": row["customer_id"],
            "amount": row["transaction_amount"],
            "transaction_amount": row["transaction_amount"],
            "transaction_type": row["transaction_type"],
            "transaction_time": row["transaction_time"],
            "merchant": row["merchant"],
            "location": row["location"],
            "device_id": row["device_id"],
            "ip_address": row["ip_address"],
            "payment_method": row["payment_method"],
            "account_balance": row["account_balance"],
            "is_international": row["is_international"],
        }
        history = customer_history(row["customer_id"])
        detection = detect(payload, history)
        save_prediction(row["transaction_id"], detection)
        alert_id = maybe_create_alert(row["transaction_id"], detection)
        payload["alert_id"] = alert_id
        if alert_id:
            maybe_investigate(payload, detection, history)
    return len(rows)
