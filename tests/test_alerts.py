from auth.authentication import create_user
from database.db import execute, fetch_one, utcnow_iso
from pipeline import process_new_transaction, verify_otp


def _baseline(user_id):
    for amount in (500, 800, 1200):
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


def test_high_creates_alert():
    user = create_user("alert@example.com", "Password@123", "Alert")
    _baseline(user["id"])
    result = process_new_transaction(
        user["id"],
        {
            "transaction_id": "ALERTHIGH",
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
    assert result["transaction"]["risk_level"] == "HIGH"
    alert = fetch_one("SELECT * FROM alerts WHERE transaction_id = ?", ("ALERTHIGH",))
    assert alert
    assert alert["severity"] == "HIGH"


def test_medium_otp_valid_and_invalid():
    user = create_user("otp@example.com", "Password@123", "OTP")
    result = process_new_transaction(
        user["id"],
        {
            "transaction_id": "OTPMED",
            "amount": 50000,
            "transaction_type": "TRANSFER",
            "beneficiary": "Priya",
            "location": "Hyderabad",
            "device_id": "DEVICE_07",
            "ip_address": "192.168.1.22",
            "transaction_time": "03:15 PM",
            "is_international": 0,
            "is_new_device": 0,
            "is_new_beneficiary": 1,
        },
    )
    txn = result["transaction"]
    assert txn["risk_level"] == "MEDIUM"
    assert result["otp_code"]
    assert txn["status"] == "PENDING_OTP"

    ok, _ = verify_otp("OTPMED", "000000")
    assert ok is False
    ok, message = verify_otp("OTPMED", result["otp_code"])
    assert ok is True
    assert "verified" in message.lower()
    stored = fetch_one("SELECT status FROM transactions WHERE transaction_id = ?", ("OTPMED",))
    assert stored["status"] == "VERIFIED"


def test_expired_otp_fails():
    user = create_user("otpexp@example.com", "Password@123", "OTPExp")
    process_new_transaction(
        user["id"],
        {
            "transaction_id": "OTPEXP",
            "amount": 900,
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
    execute(
        """
        INSERT INTO otp_verifications (transaction_id, otp_code, expires_at, verified, created_at)
        VALUES (?, ?, ?, 0, ?)
        """,
        ("OTPEXP", "654321", "2000-01-01T00:00:00+00:00", utcnow_iso()),
    )
    ok, message = verify_otp("OTPEXP", "654321")
    assert ok is False
    assert "expired" in message.lower()
