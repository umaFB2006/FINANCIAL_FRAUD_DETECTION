"""Create alerts from detection results."""

from database.database import execute, query_one
from utils.logger import get_logger

logger = get_logger(__name__)


def next_alert_id():
    row = query_one("SELECT COUNT(*) AS n FROM alerts")
    n = int(row["n"] if row else 0) + 1
    return f"ALT-{n:05d}"


def maybe_create_alert(transaction_id, detection):
    from config import Config

    if float(detection.get("risk_score") or 0) < Config.ALERT_THRESHOLD:
        return None
    existing = query_one("SELECT alert_id FROM alerts WHERE transaction_id = ?", (transaction_id,))
    if existing:
        return existing["alert_id"]
    alert_id = next_alert_id()
    reasons = detection.get("explanation", {}).get("top_reasons") or []
    message = "; ".join(reasons[:3]) or "Elevated fraud risk"
    execute(
        """
        INSERT INTO alerts (alert_id, transaction_id, severity, alert_type, alert_message, status)
        VALUES (?, ?, ?, ?, ?, 'OPEN')
        """,
        (
            alert_id,
            transaction_id,
            detection.get("severity"),
            detection.get("prediction"),
            message,
        ),
    )
    logger.info("Created alert %s for %s", alert_id, transaction_id)
    return alert_id
