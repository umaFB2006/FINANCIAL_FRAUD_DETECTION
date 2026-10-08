"""Investigation PDF reports via ReportLab."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from config import Config
from database.db import fetch_all, fetch_one, utcnow_iso
from investigation.timeline import add_event, list_events


def generate_investigation_pdf(investigation_id):
    inv = fetch_one("SELECT * FROM investigations WHERE id = ?", (investigation_id,))
    if not inv:
        raise ValueError("Investigation not found")
    txn = fetch_one(
        "SELECT * FROM transactions WHERE transaction_id = ?",
        (inv["transaction_id"],),
    )
    evidence = fetch_all(
        "SELECT * FROM evidence WHERE investigation_id = ? ORDER BY id ASC",
        (investigation_id,),
    )
    timeline = list_events(investigation_id)
    feedback = fetch_all(
        "SELECT * FROM feedback WHERE investigation_id = ? ORDER BY id ASC",
        (investigation_id,),
    )

    Config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = Config.REPORTS_DIR / f"investigation_{investigation_id}.pdf"

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(path), pagesize=A4, title=f"Investigation {investigation_id}")
    story = []
    story.append(Paragraph("Financial Fraud Investigation Report", styles["Title"]))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph(f"Investigation ID: {investigation_id}", styles["Heading2"]))
    story.append(Paragraph(f"Transaction ID: {inv['transaction_id']}", styles["Normal"]))
    story.append(Paragraph(f"Status: {inv['status']}", styles["Normal"]))
    story.append(Spacer(1, 0.15 * inch))

    if txn:
        details = [
            ["Field", "Value"],
            ["Amount", f"INR {txn['amount']:,.2f}"],
            ["Type", txn["transaction_type"]],
            ["Beneficiary", txn["beneficiary"]],
            ["Location", txn["location"]],
            ["Device", txn["device_id"]],
            ["IP", txn["ip_address"]],
            ["Time", txn["transaction_time"]],
            ["ML Score", str(txn.get("ml_score"))],
            ["Rule Score", str(txn.get("rule_score"))],
            ["Behavior Score", str(txn.get("behavior_score"))],
            ["Final Risk Score", str(txn.get("risk_score"))],
            ["Risk Level", str(txn.get("risk_level"))],
            ["Prediction", str(txn.get("prediction"))],
            ["Action", str(txn.get("recommended_action"))],
        ]
        table = Table(details, colWidths=[2.2 * inch, 4.3 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f2744")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f4f7fb")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(Paragraph("Transaction details", styles["Heading2"]))
        story.append(table)
        story.append(Spacer(1, 0.15 * inch))
        story.append(Paragraph("ML / hybrid explanation", styles["Heading2"]))
        story.append(Paragraph((txn.get("explanation") or "N/A").replace("\n", "<br/>"), styles["Normal"]))

    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("Behavior analysis", styles["Heading2"]))
    story.append(Paragraph(inv.get("summary") or "N/A", styles["Normal"]))
    story.append(Paragraph("Recommendation", styles["Heading2"]))
    story.append(Paragraph(inv.get("recommendation") or "N/A", styles["Normal"]))

    story.append(Paragraph("Evidence", styles["Heading2"]))
    if evidence:
        rows = [["Type", "Severity", "Source", "Description"]]
        for item in evidence:
            rows.append(
                [item["evidence_type"], item["severity"], item["source"], item["description"]]
            )
        ev_table = Table(rows, colWidths=[1.6 * inch, 0.9 * inch, 1.1 * inch, 2.9 * inch])
        ev_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#7a1f1f")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(ev_table)
    else:
        story.append(Paragraph("No evidence rows.", styles["Normal"]))

    story.append(Paragraph("Timeline", styles["Heading2"]))
    for event in timeline:
        story.append(
            Paragraph(
                f"{event['created_at']} — {event['event_type']}: {event['description']}",
                styles["Normal"],
            )
        )

    if feedback:
        story.append(Paragraph("Feedback", styles["Heading2"]))
        for item in feedback:
            story.append(Paragraph(f"{item['created_at']}: {item['comment']}", styles["Normal"]))

    story.append(Spacer(1, 0.25 * inch))
    story.append(
        Paragraph(
            "DISCLAIMER: This report is generated by a local synthetic-data demonstration system. "
            "It is not connected to a real bank, does not process real customer funds, and must not "
            "be used as the sole basis for legal, credit, or law-enforcement action.",
            styles["Italic"],
        )
    )
    story.append(Paragraph(f"Generated at {utcnow_iso()}", styles["Normal"]))
    doc.build(story)
    add_event(investigation_id, "REPORT_GENERATED", f"PDF report written to {path.name}.")
    return path
