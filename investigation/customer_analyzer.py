"""Customer behaviour snapshot used during investigations."""

from database.database import query_all, query_one


def get_customer(customer_id):
    return query_one("SELECT * FROM customers WHERE customer_id = ?", (customer_id,))


def customer_history(customer_id, limit=25):
    return query_all(
        """
        SELECT * FROM transactions
        WHERE customer_id = ?
        ORDER BY transaction_time DESC
        LIMIT ?
        """,
        (customer_id, limit),
    )


def typical_profile(customer_id):
    rows = customer_history(customer_id, limit=100)
    if not rows:
        return {
            "avg_amount": 0,
            "locations": [],
            "devices": [],
            "international_count": 0,
            "count": 0,
        }
    amounts = [float(r["transaction_amount"]) for r in rows]
    return {
        "avg_amount": round(sum(amounts) / len(amounts), 2),
        "max_amount": round(max(amounts), 2),
        "locations": sorted({r["location"] for r in rows if r.get("location")}),
        "devices": sorted({r["device_id"] for r in rows if r.get("device_id")}),
        "international_count": sum(int(r.get("is_international") or 0) for r in rows),
        "count": len(rows),
    }
