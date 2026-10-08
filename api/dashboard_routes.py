from flask import Blueprint, Response, request

from database.database import query_all, query_one
from services.report_service import as_csv, customer_risk_report, fraud_report, investigation_report
from utils.helpers import json_ok, login_required, role_required

bp = Blueprint("dashboard_api", __name__, url_prefix="/api")


@bp.get("/dashboard/stats")
@login_required
def stats():
    total = query_one("SELECT COUNT(*) AS n FROM transactions")["n"]
    today = query_one(
        "SELECT COUNT(*) AS n FROM transactions WHERE date(transaction_time) = date('now', 'localtime')"
    )["n"]
    fraud = query_one("SELECT COUNT(*) AS n FROM fraud_predictions WHERE prediction = 'FRAUD'")["n"]
    suspicious = query_one("SELECT COUNT(*) AS n FROM fraud_predictions WHERE prediction = 'SUSPICIOUS'")["n"]
    open_inv = query_one("SELECT COUNT(*) AS n FROM investigations WHERE case_status IN ('OPEN', 'UNDER_REVIEW', 'ESCALATED')")["n"]
    critical = query_one("SELECT COUNT(*) AS n FROM alerts WHERE severity = 'CRITICAL' AND status = 'OPEN'")["n"]
    predicted = query_one("SELECT COUNT(*) AS n FROM fraud_predictions")["n"]
    rate = round((fraud / predicted) * 100, 2) if predicted else 0
    latest_critical = query_one(
        """
        SELECT a.alert_id, a.transaction_id, a.alert_message, a.severity, p.risk_score
        FROM alerts a
        LEFT JOIN fraud_predictions p ON p.transaction_id = a.transaction_id
        WHERE a.severity = 'CRITICAL'
        ORDER BY a.created_at DESC LIMIT 1
        """
    )
    latest = query_all(
        """
        SELECT t.transaction_id, t.customer_id, t.transaction_amount, t.transaction_time,
               p.prediction, p.risk_score, a.severity
        FROM transactions t
        LEFT JOIN fraud_predictions p ON p.transaction_id = t.transaction_id
        LEFT JOIN alerts a ON a.transaction_id = t.transaction_id
        ORDER BY t.transaction_time DESC LIMIT 12
        """
    )
    return json_ok(
        {
            "total_transactions": total,
            "transactions_today": today,
            "fraud_detected": fraud,
            "suspicious_transactions": suspicious,
            "open_investigations": open_inv,
            "critical_alerts": critical,
            "fraud_detection_rate": rate,
            "latest_critical": latest_critical,
            "latest_transactions": latest,
        }
    )


@bp.get("/dashboard/charts")
@login_required
def charts():
    over_time = query_all(
        """
        SELECT date(transaction_time) AS day, COUNT(*) AS total,
               SUM(CASE WHEN p.prediction = 'FRAUD' THEN 1 ELSE 0 END) AS fraud
        FROM transactions t
        LEFT JOIN fraud_predictions p ON p.transaction_id = t.transaction_id
        GROUP BY date(transaction_time)
        ORDER BY day
        """
    )
    vs = query_all(
        """
        SELECT COALESCE(prediction, 'UNSCORED') AS label, COUNT(*) AS n
        FROM fraud_predictions
        GROUP BY prediction
        """
    )
    risk = query_all(
        """
        SELECT CASE
            WHEN risk_score <= 29 THEN 'LOW'
            WHEN risk_score <= 59 THEN 'MEDIUM'
            WHEN risk_score <= 79 THEN 'HIGH'
            ELSE 'CRITICAL'
        END AS bucket, COUNT(*) AS n
        FROM fraud_predictions
        GROUP BY bucket
        """
    )
    by_type = query_all(
        """
        SELECT t.transaction_type AS label, COUNT(*) AS n
        FROM transactions t
        JOIN fraud_predictions p ON p.transaction_id = t.transaction_id
        WHERE p.prediction = 'FRAUD'
        GROUP BY t.transaction_type
        """
    )
    by_location = query_all(
        """
        SELECT t.location AS label, COUNT(*) AS n
        FROM transactions t
        JOIN fraud_predictions p ON p.transaction_id = t.transaction_id
        WHERE p.prediction = 'FRAUD'
        GROUP BY t.location
        ORDER BY n DESC LIMIT 8
        """
    )
    by_pay = query_all(
        """
        SELECT t.payment_method AS label, COUNT(*) AS n
        FROM transactions t
        JOIN fraud_predictions p ON p.transaction_id = t.transaction_id
        WHERE p.prediction = 'FRAUD'
        GROUP BY t.payment_method
        """
    )
    alert_sev = query_all("SELECT severity AS label, COUNT(*) AS n FROM alerts GROUP BY severity")
    inv_status = query_all("SELECT case_status AS label, COUNT(*) AS n FROM investigations GROUP BY case_status")
    return json_ok(
        {
            "over_time": over_time,
            "fraud_vs_normal": vs,
            "risk_distribution": risk,
            "fraud_by_type": by_type,
            "fraud_by_location": by_location,
            "fraud_by_payment": by_pay,
            "alert_severity": alert_sev,
            "investigation_status": inv_status,
        }
    )


@bp.get("/reports/fraud")
@login_required
def reports_fraud():
    period = request.args.get("period", "daily")
    if request.args.get("format") == "csv":
        body = as_csv("fraud", period)
        return Response(body, mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=fraud_report.csv"})
    return json_ok(fraud_report(period))


@bp.get("/reports/investigations")
@login_required
def reports_investigations():
    if request.args.get("format") == "csv":
        body = as_csv("investigations")
        return Response(
            body,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=investigations.csv"},
        )
    return json_ok(investigation_report())


@bp.get("/reports/customers")
@role_required("ADMIN", "INVESTIGATOR")
def reports_customers():
    if request.args.get("format") == "csv":
        body = as_csv("customers")
        return Response(
            body,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=customer_risk.csv"},
        )
    return json_ok(customer_risk_report())
