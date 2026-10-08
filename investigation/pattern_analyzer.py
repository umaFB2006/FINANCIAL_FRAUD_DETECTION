"""Pattern checks across related customer activity."""


def analyze_patterns(txn, history, features):
    patterns = []
    related = []
    amount = float(txn.get("amount") or txn.get("transaction_amount") or 0)
    for row in history:
        if row.get("transaction_id") == txn.get("transaction_id"):
            continue
        related.append(
            {
                "transaction_id": row["transaction_id"],
                "amount": row["transaction_amount"],
                "location": row["location"],
                "device_id": row["device_id"],
                "time": row["transaction_time"],
            }
        )

    if features.get("unusual_device"):
        patterns.append("Unseen device relative to customer history")
    if features.get("unusual_location"):
        patterns.append("Location does not match usual activity")
    if int(features.get("velocity_count") or 0) >= 4:
        patterns.append("High transaction velocity (multiple events in minutes)")
    if int(features.get("is_international") or 0):
        patterns.append("Cross-border payment")
    merchants = [r.get("merchant") for r in history]
    if txn.get("merchant") and merchants.count(txn.get("merchant")) >= 3:
        patterns.append("Repeated merchant activity")
    avg = float(features.get("avg_amount") or 1)
    if amount > avg * 5:
        patterns.append("Spend spike versus historical average")

    return {
        "patterns": patterns or ["No additional historical pattern beyond the current score"],
        "related_transactions": related[:10],
    }
