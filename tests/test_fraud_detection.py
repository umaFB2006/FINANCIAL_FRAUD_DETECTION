from auth.authentication import create_user
from ml.fraud_detector import FraudDetector
from pipeline import process_new_transaction


def test_ml_prediction_shape():
    det = FraudDetector()
    result = det.predict(
        {
            "amount": 150000,
            "transaction_type": "TRANSFER",
            "transaction_time": "02:30 AM",
            "is_international": 1,
            "is_new_device": 1,
            "is_new_beneficiary": 1,
        }
    )
    assert 0 <= result["ml_score"] <= 100
    assert 0 <= result["fraud_probability"] <= 1
    assert result["prediction"] in {"FRAUD", "LEGITIMATE"}


def test_low_medium_high_identification():
    user = create_user("risklevels@example.com", "Password@123", "Levels")
    for amount in (500, 800, 1200, 900, 1500):
        process_new_transaction(
            user["id"],
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
    low = process_new_transaction(
        user["id"],
        {
            "transaction_id": "LVL_LOW",
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
    medium = process_new_transaction(
        user["id"],
        {
            "transaction_id": "LVL_MED",
            "amount": 25000,
            "transaction_type": "TRANSFER",
            "beneficiary": "Priya",
            "location": "Hyderabad",
            "device_id": "DEVICE_01",
            "ip_address": "192.168.1.10",
            "transaction_time": "03:15 PM",
            "is_international": 0,
            "is_new_device": 0,
            "is_new_beneficiary": 1,
        },
    )
    high = process_new_transaction(
        user["id"],
        {
            "transaction_id": "LVL_HIGH",
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
    assert low["transaction"]["risk_level"] == "LOW"
    assert high["transaction"]["risk_level"] == "HIGH"
    assert high["transaction"]["risk_score"] > low["transaction"]["risk_score"]
    assert medium["transaction"]["risk_level"] in {"MEDIUM", "HIGH"}
    if medium["transaction"]["risk_level"] == "MEDIUM":
        assert medium["transaction"]["status"] == "PENDING_OTP"
    assert high["investigation"] is not None
    assert "New device" in high["transaction"]["explanation"] or "new device" in high["transaction"]["explanation"].lower()
