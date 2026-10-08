from database.db import fetch_all, fetch_one
from pipeline import process_new_transaction
from tests.conftest import signup_and_login


def _user_id(email):
    return fetch_one("SELECT id FROM users WHERE email = ?", (email,))["id"]


def _payload(txn_id, amount, **overrides):
    data = {
        "transaction_id": txn_id,
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
    }
    data.update(overrides)
    return data


def test_user_can_create_transaction(client):
    signup_and_login(client, "txn@example.com")
    resp = client.post(
        "/transaction",
        data={
            "transaction_id": "TXNUI1",
            "amount": "900",
            "transaction_type": "UPI",
            "beneficiary": "ABC",
            "location": "Hyderabad",
            "device_id": "DEVICE_01",
            "ip_address": "10.0.0.2",
            "transaction_time": "10:00 AM",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert fetch_one("SELECT * FROM transactions WHERE transaction_id = ?", ("TXNUI1",))


def test_transaction_saved_and_scores_present():
    from auth.authentication import create_user

    user = create_user("save@example.com", "Password@123", "Save")
    result = process_new_transaction(user["id"], _payload("TXNSAVE1", 900))
    assert result["ok"]
    txn = result["transaction"]
    assert txn["ml_score"] is not None
    assert txn["rule_score"] is not None
    assert txn["behavior_score"] is not None
    assert txn["risk_score"] is not None
    assert txn["explanation"]


def test_multiple_transactions_persist():
    from auth.authentication import create_user

    user = create_user("multi@example.com", "Password@123", "Multi")
    r1 = process_new_transaction(user["id"], _payload("TXNM1", 500))
    r2 = process_new_transaction(user["id"], _payload("TXNM2", 800))
    r3 = process_new_transaction(user["id"], _payload("TXNM3", 1200))
    assert r1["ok"] and r2["ok"] and r3["ok"]
    rows = fetch_all("SELECT transaction_id FROM transactions WHERE user_id = ? ORDER BY id", (user["id"],))
    ids = [r["transaction_id"] for r in rows]
    assert ids == ["TXNM1", "TXNM2", "TXNM3"]
    assert r3["profile"]["count"] == 2
    assert r3["profile"]["has_history"]


def test_history_page_and_filter(client):
    signup_and_login(client, "hist@example.com")
    uid = _user_id("hist@example.com")
    process_new_transaction(uid, _payload("HIST1", 900))
    process_new_transaction(
        uid,
        _payload(
            "HIST2",
            150000,
            transaction_type="TRANSFER",
            beneficiary="Rahul",
            location="Mumbai",
            device_id="DEVICE_NEW_99",
            transaction_time="02:30 AM",
            is_international=1,
            is_new_device=1,
            is_new_beneficiary=1,
        ),
    )
    page = client.get("/history")
    assert b"HIST1" in page.data
    assert b"HIST2" in page.data
    filtered = client.get("/history?risk_level=HIGH")
    assert b"HIST2" in filtered.data
