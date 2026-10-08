"""CSV report builders from live database rows."""

import csv
import io
from datetime import datetime, timedelta

from database.database import query_all


def _csv(rows, fieldnames):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def fraud_report(period="daily"):
    days = {"daily": 1, "weekly": 7, "monthly": 30}.get(period, 1)
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    rows = query_all(
        """
        SELECT t.transaction_id, t.customer_id, t.transaction_amount, t.transaction_type,
               t.location, t.payment_method, t.transaction_time,
               p.prediction, p.risk_score, p.fraud_probability
        FROM transactions t
        JOIN fraud_predictions p ON p.transaction_id = t.transaction_id
        WHERE t.transaction_time >= ? AND p.prediction IN ('FRAUD', 'SUSPICIOUS')
        ORDER BY p.risk_score DESC
        """,
        (since,),
    )
    summary = {
        "period": period,
        "since": since,
        "count": len(rows),
        "avg_risk": round(sum(float(r["risk_score"]) for r in rows) / len(rows), 2) if rows else 0,
        "rows": rows,
    }
    return summary


def investigation_report():
    rows = query_all(
        """
        SELECT investigation_id, transaction_id, case_status, recommendation,
               investigator, created_at, updated_at
        FROM investigations
        ORDER BY created_at DESC
        """
    )
    return {"count": len(rows), "rows": rows}


def customer_risk_report():
    rows = query_all(
        """
        SELECT t.customer_id, COUNT(*) AS txn_count,
               AVG(p.risk_score) AS avg_risk,
               SUM(CASE WHEN p.prediction = 'FRAUD' THEN 1 ELSE 0 END) AS fraud_count
        FROM transactions t
        JOIN fraud_predictions p ON p.transaction_id = t.transaction_id
        GROUP BY t.customer_id
        ORDER BY avg_risk DESC
        """
    )
    return {"count": len(rows), "rows": rows}


def as_csv(kind, period="daily"):
    if kind == "fraud":
        data = fraud_report(period)
        return _csv(
            data["rows"],
            [
                "transaction_id",
                "customer_id",
                "transaction_amount",
                "prediction",
                "risk_score",
                "transaction_time",
            ],
        )
    if kind == "investigations":
        data = investigation_report()
        return _csv(
            data["rows"],
            [
                "investigation_id",
                "transaction_id",
                "case_status",
                "recommendation",
                "investigator",
                "created_at",
            ],
        )
    data = customer_risk_report()
    return _csv(data["rows"], ["customer_id", "txn_count", "avg_risk", "fraud_count"])
