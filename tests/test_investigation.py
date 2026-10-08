from auth.authentication import create_user
from database.db import fetch_all, fetch_one
from investigation.investigator import update_status
from pipeline import process_new_transaction


def _high_txn(user_id, txn_id="INVHIGH1"):
    for amount in (500, 800, 900):
        process_new_transaction(
            user_id,
            {
                "amount": amount,
                "transaction_type": "UPI",
                "beneficiary": "ABC",
                "location": "Hyderabad",
                "device_id": "DEVICE_01",
                "ip_address": "192.168.1.10",
                "transaction_time": "11:00 AM",
                "is_international": 0,
                "is_new_device": 0,
                "is_new_beneficiary": 0,
            },
        )
    return process_new_transaction(
        user_id,
        {
            "transaction_id": txn_id,
            "amount": 150000,
            "transaction_type": "TRANSFER",
            "beneficiary": "Rahul",
            "location": "Mumbai",
            "device_id": "DEVICE_NEW_99",
            "ip_address": "192.168.1.50",
            "transaction_time": "02:30 AM",
            "is_international": 1,
            "is_new_device": 1,
            "is_new_beneficiary": 1,
        },
    )


def test_high_creates_investigation_evidence_timeline():
    user = create_user("inv@example.com", "Password@123", "Inv")
    result = _high_txn(user["id"])
    assert result["transaction"]["risk_level"] == "HIGH"
    inv = result["investigation"]
    assert inv is not None
    assert inv["status"] == "OPEN"
    evidence = fetch_all("SELECT * FROM evidence WHERE investigation_id = ?", (inv["id"],))
    assert evidence
    events = fetch_all("SELECT event_type FROM timeline_events WHERE investigation_id = ?", (inv["id"],))
    types = {e["event_type"] for e in events}
    assert "INVESTIGATION_CREATED" in types
    assert "EVIDENCE_GENERATED" in types
    assert "ANALYSIS_COMPLETED" in types


def test_investigator_can_update_status_and_feedback(client):
    from auth.authentication import create_user as cu

    investigator = cu("investigator.case@example.com", "Password@123", "Case Officer", "INVESTIGATOR")
    user = cu("cust@example.com", "Password@123", "Cust")
    result = _high_txn(user["id"], "INVHIGH2")
    inv_id = result["investigation"]["id"]
    client.post(
        "/login",
        data={"email": "investigator.case@example.com", "password": "Password@123"},
        follow_redirects=True,
    )
    page = client.get(f"/investigation/{inv_id}")
    assert page.status_code == 200
    client.post(
        f"/investigation/{inv_id}",
        data={"status": "INVESTIGATING", "assign_to_self": "y"},
        follow_redirects=True,
    )
    updated = fetch_one("SELECT * FROM investigations WHERE id = ?", (inv_id,))
    assert updated["status"] == "INVESTIGATING"
    client.post(
        f"/investigation/{inv_id}/feedback",
        data={"comment": "Reviewed device telemetry."},
        follow_redirects=True,
    )
    comments = fetch_all("SELECT * FROM feedback WHERE investigation_id = ?", (inv_id,))
    assert comments
    update_status(inv_id, "CONFIRMED_FRAUD", "tester")
    assert fetch_one("SELECT status FROM investigations WHERE id = ?", (inv_id,))["status"] == "CONFIRMED_FRAUD"


def test_dashboard_pages(client):
    from auth.authentication import create_user as cu

    cu("admin.dash@example.com", "Password@123", "Admin", "ADMIN")
    cu("inv.dash@example.com", "Password@123", "Inv", "INVESTIGATOR")
    client.post("/login", data={"email": "admin.dash@example.com", "password": "Password@123"}, follow_redirects=True)
    admin_page = client.get("/admin")
    assert admin_page.status_code == 200
    assert b"Total Users" in admin_page.data
    client.get("/logout")
    client.post("/login", data={"email": "inv.dash@example.com", "password": "Password@123"}, follow_redirects=True)
    inv_page = client.get("/investigator")
    assert inv_page.status_code == 200
    assert b"Open investigations" in inv_page.data
