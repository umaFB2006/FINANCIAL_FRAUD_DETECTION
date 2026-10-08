"""Investigation service wrapping case manager for APIs."""

from database.database import query_all, query_one
from investigation.case_manager import get_case, update_case
from investigation.investigation_report import case_report_payload


def list_investigations(status=None):
    sql = """
        SELECT i.*, t.customer_id, t.transaction_amount, p.risk_score, a.severity
        FROM investigations i
        JOIN transactions t ON t.transaction_id = i.transaction_id
        LEFT JOIN fraud_predictions p ON p.transaction_id = t.transaction_id
        LEFT JOIN alerts a ON a.alert_id = i.alert_id
        WHERE (? IS NULL OR i.case_status = ?)
        GROUP BY i.investigation_id
        ORDER BY i.created_at DESC
    """
    return query_all(sql, (status, status))


def investigation_detail(investigation_id):
    case = get_case(investigation_id)
    if not case:
        return None
    txn = query_one("SELECT * FROM transactions WHERE transaction_id = ?", (case["transaction_id"],))
    pred = query_one(
        """
        SELECT * FROM fraud_predictions
        WHERE transaction_id = ?
        ORDER BY prediction_id DESC LIMIT 1
        """,
        (case["transaction_id"],),
    )
    customer = query_one("SELECT * FROM customers WHERE customer_id = ?", (txn["customer_id"],)) if txn else None
    related = query_all(
        """
        SELECT t.*, p.risk_score, p.prediction
        FROM transactions t
        LEFT JOIN fraud_predictions p ON p.transaction_id = t.transaction_id
        WHERE t.customer_id = ? AND t.transaction_id != ?
        ORDER BY t.transaction_time DESC LIMIT 10
        """,
        (txn["customer_id"], txn["transaction_id"]),
    ) if txn else []
    report = case_report_payload(investigation_id)
    case["transaction"] = txn
    case["prediction"] = pred
    case["customer"] = customer
    case["related_transactions"] = related
    case["report"] = report
    return case


def apply_update(investigation_id, payload, user_id=None, username=None):
    return update_case(
        investigation_id,
        status=payload.get("case_status") or payload.get("status"),
        notes=payload.get("notes"),
        decision=payload.get("final_decision") or payload.get("decision"),
        user_id=user_id,
        investigator=username,
    )
