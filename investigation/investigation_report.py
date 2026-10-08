"""Build a narrative investigation report for a case."""

from investigation.case_manager import get_case


def generate_report_text(case, txn, detection, customer, patterns):
    reasons = detection.get("explanation", {}).get("top_reasons") or []
    evidence = detection.get("explanation", {}).get("top_reasons") or []
    related = patterns.get("related_transactions") or []
    lines = [
        "INVESTIGATION CASE",
        f"Case ID: {case}",
        f"Risk Level: {detection.get('severity')}",
        f"Fraud Probability: {round(float(detection.get('fraud_probability', 0)) * 100)}%",
        "",
        "Reason:",
        " ".join(reasons) or "Automated risk review.",
        "",
        "Evidence:",
    ]
    for i, item in enumerate(evidence, start=1):
        lines.append(f"{i}. {item}")
    lines += [
        "",
        f"Customer: {customer.get('customer_id') if customer else 'N/A'} ({(customer or {}).get('name', '')})",
        f"Transaction: {txn.get('transaction_id')} amount={txn.get('amount') or txn.get('transaction_amount')}",
        f"Related transactions reviewed: {len(related)}",
        "",
        f"Recommendation: {detection.get('recommendation', 'MONITOR')}",
        "",
        "This report is a simulated academic investigation. No real account action was taken.",
    ]
    return "\n".join(lines)


def case_report_payload(investigation_id):
    case = get_case(investigation_id)
    if not case:
        return None
    return {
        "investigation_id": case["investigation_id"],
        "status": case["case_status"],
        "summary": case["investigation_summary"],
        "recommendation": case["recommendation"],
        "evidence": case["evidence"],
        "events": case["events"],
    }
