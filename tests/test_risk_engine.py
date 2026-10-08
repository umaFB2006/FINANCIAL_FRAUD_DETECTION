from ml.behaviour_profiler import build_profile, calculate_behavior_score
from ml.risk_engine import calculate_final_risk, calculate_rule_score, classify_risk


def test_rule_score_bounds_and_signals():
    low = calculate_rule_score(
        {"amount": 900, "is_international": 0, "is_new_device": 0, "is_new_beneficiary": 0, "transaction_time": "11:00 AM", "transaction_type": "UPI"}
    )
    high = calculate_rule_score(
        {"amount": 150000, "is_international": 1, "is_new_device": 1, "is_new_beneficiary": 1, "transaction_time": "02:30 AM", "transaction_type": "TRANSFER"}
    )
    assert 0 <= low <= 100
    assert 0 <= high <= 100
    assert high > low


def test_hybrid_weights_and_levels():
    score, level, action = calculate_final_risk(20, 10, 10)
    assert level == "LOW"
    assert action == "AUTO_APPROVED"
    score, level, action = calculate_final_risk(50, 50, 50)
    assert level == "MEDIUM"
    assert action == "ADDITIONAL_VERIFICATION"
    score, level, action = calculate_final_risk(90, 90, 90)
    assert abs(score - 90) < 0.01
    assert level == "HIGH"
    assert action == "UNDER_INVESTIGATION"


def test_classify_boundaries():
    assert classify_risk(30)[0] == "LOW"
    assert classify_risk(31)[0] == "MEDIUM"
    assert classify_risk(70)[0] == "MEDIUM"
    assert classify_risk(71)[0] == "HIGH"


def test_behavior_profile_uses_history():
    history = [
        {"amount": 500, "location": "Hyderabad", "device_id": "DEVICE_01", "beneficiary": "ABC", "transaction_type": "UPI", "transaction_time": "10:00 AM", "is_international": 0, "is_new_device": 0, "is_new_beneficiary": 0},
        {"amount": 800, "location": "Hyderabad", "device_id": "DEVICE_01", "beneficiary": "ABC", "transaction_type": "UPI", "transaction_time": "11:00 AM", "is_international": 0, "is_new_device": 0, "is_new_beneficiary": 0},
        {"amount": 1200, "location": "Hyderabad", "device_id": "DEVICE_01", "beneficiary": "ABC", "transaction_type": "UPI", "transaction_time": "02:00 PM", "is_international": 0, "is_new_device": 0, "is_new_beneficiary": 0},
    ]
    profile = build_profile(history)
    assert profile["has_history"]
    assert profile["count"] == 3
    assert profile["common_location"] == "Hyderabad"
    normal, _ = calculate_behavior_score(
        {"amount": 900, "location": "Hyderabad", "device_id": "DEVICE_01", "beneficiary": "ABC", "transaction_type": "UPI", "transaction_time": "11:00 AM", "is_international": 0, "is_new_device": 0, "is_new_beneficiary": 0},
        profile,
    )
    anomalous, reasons = calculate_behavior_score(
        {"amount": 150000, "location": "Mumbai", "device_id": "DEVICE_NEW_99", "beneficiary": "Rahul", "transaction_type": "TRANSFER", "transaction_time": "02:30 AM", "is_international": 1, "is_new_device": 1, "is_new_beneficiary": 1},
        profile,
    )
    assert anomalous > normal
    assert any("amount" in r.lower() for r in reasons)
