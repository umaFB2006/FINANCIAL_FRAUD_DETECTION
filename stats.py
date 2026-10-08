"""Dynamic dashboard statistics from SQLite."""

from database.db import fetch_all, fetch_one


def _count(query, params=()):
    row = fetch_one(query, params)
    return int(row["c"]) if row else 0


def user_dashboard_stats(user_id=None, role="USER"):
    if role == "USER" and user_id is not None:
        where = "WHERE user_id = ?"
        params = (user_id,)
    else:
        where = ""
        params = ()

    total = _count(f"SELECT COUNT(*) AS c FROM transactions {where}", params)
    legit = _count(
        f"SELECT COUNT(*) AS c FROM transactions {where} {'AND' if where else 'WHERE'} prediction = 'LEGITIMATE'",
        params,
    )
    suspicious = _count(
        f"SELECT COUNT(*) AS c FROM transactions {where} {'AND' if where else 'WHERE'} prediction = 'SUSPICIOUS'",
        params,
    )
    fraud = _count(
        f"SELECT COUNT(*) AS c FROM transactions {where} {'AND' if where else 'WHERE'} prediction = 'FRAUD'",
        params,
    )
    low = _count(
        f"SELECT COUNT(*) AS c FROM transactions {where} {'AND' if where else 'WHERE'} risk_level = 'LOW'",
        params,
    )
    medium = _count(
        f"SELECT COUNT(*) AS c FROM transactions {where} {'AND' if where else 'WHERE'} risk_level = 'MEDIUM'",
        params,
    )
    high = _count(
        f"SELECT COUNT(*) AS c FROM transactions {where} {'AND' if where else 'WHERE'} risk_level = 'HIGH'",
        params,
    )
    avg_row = fetch_one(
        f"SELECT AVG(risk_score) AS a FROM transactions {where}",
        params,
    )
    avg_risk = round(float(avg_row["a"] or 0), 2)

    if role == "USER" and user_id is not None:
        active_inv = _count(
            "SELECT COUNT(*) AS c FROM investigations WHERE user_id = ? AND status IN ('OPEN','INVESTIGATING')",
            (user_id,),
        )
        resolved_inv = _count(
            "SELECT COUNT(*) AS c FROM investigations WHERE user_id = ? AND status IN ('RESOLVED','FALSE_POSITIVE','CONFIRMED_FRAUD')",
            (user_id,),
        )
    else:
        active_inv = _count(
            "SELECT COUNT(*) AS c FROM investigations WHERE status IN ('OPEN','INVESTIGATING')"
        )
        resolved_inv = _count(
            "SELECT COUNT(*) AS c FROM investigations WHERE status IN ('RESOLVED','FALSE_POSITIVE','CONFIRMED_FRAUD')"
        )

    return {
        "total": total,
        "legitimate": legit,
        "suspicious": suspicious,
        "fraud": fraud,
        "low": low,
        "medium": medium,
        "high": high,
        "active_investigations": active_inv,
        "resolved_investigations": resolved_inv,
        "average_risk": avg_risk,
    }


def admin_stats():
    base = user_dashboard_stats(role="ADMIN")
    base.update(
        {
            "total_users": _count("SELECT COUNT(*) AS c FROM users"),
            "confirmed_fraud": _count(
                "SELECT COUNT(*) AS c FROM investigations WHERE status = 'CONFIRMED_FRAUD'"
            ),
            "false_positives": _count(
                "SELECT COUNT(*) AS c FROM investigations WHERE status = 'FALSE_POSITIVE'"
            ),
            "users": fetch_all(
                "SELECT id, email, full_name, role, created_at FROM users ORDER BY id ASC"
            ),
            "recent_alerts": fetch_all(
                "SELECT * FROM alerts ORDER BY datetime(created_at) DESC, id DESC LIMIT 10"
            ),
            "fraud_trend": fetch_all(
                """
                SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS c
                FROM transactions
                WHERE prediction = 'FRAUD'
                GROUP BY substr(created_at, 1, 10)
                ORDER BY day ASC
                """
            ),
        }
    )
    return base


def investigator_stats():
    return {
        "open": _count("SELECT COUNT(*) AS c FROM investigations WHERE status = 'OPEN'"),
        "investigating": _count(
            "SELECT COUNT(*) AS c FROM investigations WHERE status = 'INVESTIGATING'"
        ),
        "high_risk_tx": _count("SELECT COUNT(*) AS c FROM transactions WHERE risk_level = 'HIGH'"),
        "confirmed_fraud": _count(
            "SELECT COUNT(*) AS c FROM investigations WHERE status = 'CONFIRMED_FRAUD'"
        ),
        "active": _count(
            "SELECT COUNT(*) AS c FROM investigations WHERE status IN ('OPEN','INVESTIGATING')"
        ),
    }
