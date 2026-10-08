"""Narrative investigation summaries."""


def generate_summary(txn, analysis, evidence_items):
    evidence_types = ", ".join(item[0] for item in evidence_items) or "none"
    return (
        f"Investigation opened for transaction {txn.get('transaction_id')} "
        f"(₹{float(txn.get('amount') or 0):,.2f} {txn.get('transaction_type')}). "
        f"Final risk score {txn.get('risk_score')} ({txn.get('risk_level')}). "
        f"User history count: {analysis.get('history_count')}. "
        f"Evidence indicators: {evidence_types}."
    )


def generate_recommendation(risk_level):
    if risk_level == "HIGH":
        return "Block pending review. Contact the customer through an out-of-band channel and verify beneficiary, device, and travel status."
    if risk_level == "MEDIUM":
        return "Hold for additional verification (OTP / step-up authentication) before release."
    return "No further action required. Transaction can remain auto-approved."
