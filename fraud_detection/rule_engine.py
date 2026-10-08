"""Rule-based fraud signals that complement ML scores."""

from config import Config


def evaluate_rules(feature_row, txn):
    hits = []
    amount = float(txn.get("amount") or txn.get("transaction_amount") or 0)
    avg = float(feature_row.get("avg_amount") or amount or 1)
    velocity = int(feature_row.get("velocity_count") or 1)

    if amount >= avg * 5 and avg > 0:
        hits.append({"rule": "RULE_1", "weight": 25, "message": "Transaction amount is unusually high"})
    if velocity >= 4:
        hits.append({"rule": "RULE_2", "weight": 20, "message": "Many transactions occurred within a short time"})
    if feature_row.get("unusual_location"):
        hits.append({"rule": "RULE_3", "weight": 15, "message": "Transaction location is unusual for this customer"})
    if feature_row.get("unusual_device") and amount >= max(avg * 3, 10000):
        hits.append({"rule": "RULE_4", "weight": 20, "message": "New device used for a high-value transaction"})
    if int(feature_row.get("is_international") or 0) == 1:
        hits.append({"rule": "RULE_5", "weight": 15, "message": "International transaction occurred unexpectedly"})
    if float(feature_row.get("amount_deviation") or 0) >= 2:
        hits.append({"rule": "RULE_6", "weight": 15, "message": "Amount differs significantly from customer history"})
    if len(hits) >= 3:
        hits.append({"rule": "RULE_7", "weight": 15, "message": "Multiple risk indicators occurred together"})

    score = min(100, sum(h["weight"] for h in hits))
    return {"rule_score": score, "triggered_rules": hits}
