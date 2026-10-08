from flask import Blueprint, request

from database.database import query_all, query_one
from fraud_detection.transaction_validator import validate_transaction
from services.transaction_service import process_transaction
from utils.helpers import json_error, json_ok, login_required

bp = Blueprint("transactions_api", __name__, url_prefix="/api/transactions")


@bp.post("")
@login_required
def create_transaction():
    payload = request.get_json(silent=True) or {}
    check = validate_transaction(payload)
    if not check["valid"]:
        return json_error("; ".join(check["errors"]), 400)
    try:
        result = process_transaction(payload)
    except ValueError as exc:
        return json_error(str(exc), 400)
    return json_ok(result, status=201)


@bp.get("")
@login_required
def list_transactions():
    q = (request.args.get("q") or "").strip()
    prediction = request.args.get("prediction")
    page = max(int(request.args.get("page") or 1), 1)
    per_page = min(max(int(request.args.get("per_page") or 15), 1), 100)
    offset = (page - 1) * per_page
    where = ["1=1"]
    params = []
    if q:
        where.append("(t.transaction_id LIKE ? OR t.customer_id LIKE ? OR t.location LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like, like])
    if prediction:
        where.append("p.prediction = ?")
        params.append(prediction)
    clause = " AND ".join(where)
    total_row = query_one(
        f"""
        SELECT COUNT(*) AS n
        FROM transactions t
        LEFT JOIN fraud_predictions p ON p.transaction_id = t.transaction_id
        WHERE {clause}
        """,
        tuple(params),
    )
    rows = query_all(
        f"""
        SELECT t.*, p.prediction, p.risk_score, p.fraud_probability, a.severity, a.alert_id,
               i.investigation_id
        FROM transactions t
        LEFT JOIN fraud_predictions p ON p.transaction_id = t.transaction_id
        LEFT JOIN alerts a ON a.transaction_id = t.transaction_id
        LEFT JOIN investigations i ON i.transaction_id = t.transaction_id
        WHERE {clause}
        GROUP BY t.transaction_id
        ORDER BY t.transaction_time DESC
        LIMIT ? OFFSET ?
        """,
        tuple(params + [per_page, offset]),
    )
    return json_ok({"items": rows, "page": page, "per_page": per_page, "total": total_row["n"] if total_row else 0})


@bp.get("/<transaction_id>")
@login_required
def transaction_detail(transaction_id):
    txn = query_one("SELECT * FROM transactions WHERE transaction_id = ?", (transaction_id,))
    if not txn:
        return json_error("Transaction not found", 404)
    pred = query_one(
        """
        SELECT * FROM fraud_predictions
        WHERE transaction_id = ? ORDER BY prediction_id DESC LIMIT 1
        """,
        (transaction_id,),
    )
    alert = query_one("SELECT * FROM alerts WHERE transaction_id = ?", (transaction_id,))
    case = query_one("SELECT * FROM investigations WHERE transaction_id = ?", (transaction_id,))
    related = query_all(
        """
        SELECT t.transaction_id, t.transaction_amount, t.location, t.device_id,
               t.transaction_time, p.prediction, p.risk_score
        FROM transactions t
        LEFT JOIN fraud_predictions p ON p.transaction_id = t.transaction_id
        WHERE t.customer_id = ? AND t.transaction_id != ?
        ORDER BY t.transaction_time DESC LIMIT 12
        """,
        (txn["customer_id"], transaction_id),
    )
    customer = query_one("SELECT * FROM customers WHERE customer_id = ?", (txn["customer_id"],))
    return json_ok(
        {
            "transaction": txn,
            "prediction": pred,
            "alert": alert,
            "investigation": case,
            "related_transactions": related,
            "customer": customer,
        }
    )
