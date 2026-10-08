"""Create tables and idempotent demo data."""

from __future__ import annotations

from auth.authentication import create_user, hash_password
from database.db import execute, fetch_one, init_db, utcnow_iso
from pipeline import process_new_transaction

DEMO_USERS = [
    ("user@example.com", "Password@123", "Demo User", "USER"),
    ("investigator@example.com", "Password@123", "Demo Investigator", "INVESTIGATOR"),
    ("admin@example.com", "Password@123", "Demo Admin", "ADMIN"),
]


def ensure_user(email, password, full_name, role):
    existing = fetch_one("SELECT * FROM users WHERE email = ?", (email,))
    if existing:
        return existing
    try:
        return create_user(email, password, full_name, role)
    except ValueError:
        user_id = execute(
            "INSERT INTO users (email, password_hash, full_name, role, created_at) VALUES (?, ?, ?, ?, ?)",
            (email, hash_password(password), full_name, role, utcnow_iso()),
        )
        return fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))


def seed_user_history(user_id):
    baseline = [
        {"transaction_id": "SEED_U_500", "amount": 500, "beneficiary": "ABC", "time": "10:15 AM"},
        {"transaction_id": "SEED_U_800", "amount": 800, "beneficiary": "ABC", "time": "11:40 AM"},
        {"transaction_id": "SEED_U_1200", "amount": 1200, "beneficiary": "ABC", "time": "02:10 PM"},
        {"transaction_id": "SEED_U_900", "amount": 900, "beneficiary": "ABC", "time": "04:05 PM"},
        {"transaction_id": "SEED_U_1500", "amount": 1500, "beneficiary": "ABC", "time": "06:20 PM"},
    ]
    for item in baseline:
        if fetch_one("SELECT id FROM transactions WHERE transaction_id = ?", (item["transaction_id"],)):
            continue
        process_new_transaction(
            user_id,
            {
                "transaction_id": item["transaction_id"],
                "amount": item["amount"],
                "transaction_type": "UPI",
                "beneficiary": item["beneficiary"],
                "location": "Hyderabad",
                "device_id": "DEVICE_01",
                "ip_address": "192.168.1.10",
                "transaction_time": item["time"],
                "is_international": 0,
                "is_new_device": 0,
                "is_new_beneficiary": 0,
            },
        )


def seed_examples(user_id):
    samples = [
        {
            "transaction_id": "SEED_LOW_900",
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
        {
            "transaction_id": "SEED_MED_25000",
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
        {
            "transaction_id": "SEED_HIGH_150000",
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
    ]
    for payload in samples:
        if fetch_one("SELECT id FROM transactions WHERE transaction_id = ?", (payload["transaction_id"],)):
            continue
        process_new_transaction(user_id, payload)


def main():
    init_db()
    users = [ensure_user(*row) for row in DEMO_USERS]
    demo_user = users[0]
    seed_user_history(demo_user["id"])
    seed_examples(demo_user["id"])
    print("Database seeded.")
    print("Demo accounts:")
    print("  USER          user@example.com / Password@123")
    print("  INVESTIGATOR  investigator@example.com / Password@123")
    print("  ADMIN         admin@example.com / Password@123")


if __name__ == "__main__":
    main()
