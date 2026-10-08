from flask import Blueprint, request

from database.database import query_all, query_one
from fraud_detection.detector import detect
from fraud_detection.transaction_validator import validate_transaction
from investigation.customer_analyzer import customer_history
from services.transaction_service import process_transaction
from utils.helpers import json_error, json_ok, login_required

bp = Blueprint("fraud_api", __name__, url_prefix="/api")


@bp.post("/fraud/predict")
@login_required
def predict():
    payload = request.get_json(silent=True) or {}
    persist = bool(payload.pop("persist", False))
    check = validate_transaction(payload)
    if not check["valid"]:
        return json_error("; ".join(check["errors"]), 400)
    if persist:
        try:
            return json_ok(process_transaction(payload), status=201)
        except ValueError as exc:
            return json_error(str(exc), 400)
    history = customer_history(payload.get("customer_id"))
    payload["amount"] = float(payload["amount"])
    result = detect(payload, history)
    return json_ok(result)


@bp.get("/alerts")
@login_required
def list_alerts():
    severity = request.args.get("severity")
    status = request.args.get("status")
    rows = query_all(
        """
        SELECT a.*, t.customer_id, t.transaction_amount, p.risk_score
        FROM alerts a
        JOIN transactions t ON t.transaction_id = a.transaction_id
        LEFT JOIN fraud_predictions p ON p.transaction_id = a.transaction_id
        WHERE (? IS NULL OR a.severity = ?)
          AND (? IS NULL OR a.status = ?)
        ORDER BY a.created_at DESC
        """,
        (severity, severity, status, status),
    )
    return json_ok(rows)


@bp.get("/alerts/<alert_id>")
@login_required
def get_alert(alert_id):
    row = query_one("SELECT * FROM alerts WHERE alert_id = ?", (alert_id,))
    if not row:
        return json_error("Alert not found", 404)
    return json_ok(row)
