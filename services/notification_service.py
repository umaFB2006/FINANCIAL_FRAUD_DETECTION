"""Notification placeholders for the academic demo."""

from utils.logger import get_logger

logger = get_logger(__name__)


def notify_critical(alert_id, transaction_id, risk_score, reasons):
    logger.info(
        "CRITICAL NOTICE alert=%s txn=%s risk=%s reasons=%s",
        alert_id,
        transaction_id,
        risk_score,
        reasons,
    )
    return {
        "delivered": False,
        "channel": "in_app",
        "message": f"Critical fraud alert {alert_id} for {transaction_id}",
    }
