"""Generate synthetic customers/transactions and seed the SQLite database."""

from __future__ import annotations

import argparse
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import Config  # noqa: E402
from database.database import execute, get_connection, init_db  # noqa: E402
from utils.constants import PAYMENT_METHODS, TRANSACTION_TYPES  # noqa: E402
from utils.helpers import hash_password  # noqa: E402
from utils.logger import get_logger  # noqa: E402

logger = get_logger(__name__)

LOCATIONS = [
    "Hyderabad",
    "Mumbai",
    "Bengaluru",
    "Chennai",
    "Pune",
    "Kolkata",
    "Ahmedabad",
    "New Delhi",
    "Jaipur",
]
INTL_LOCATIONS = ["London", "Dubai", "Singapore", "New York"]
MERCHANTS = [
    "Grocery Mart",
    "Fuel Station",
    "Online Store",
    "Restaurant",
    "Electronics Hub",
    "Pharmacy",
    "Streaming Sub",
    "Utility Bill",
    "Travel Booking",
    "Unknown Merchant",
]


def _random_ip():
    return f"103.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"


def generate_customers(n=50):
    customers = []
    for i in range(1, n + 1):
        cid = f"CUST{i:03d}"
        customers.append(
            {
                "customer_id": cid,
                "name": f"Synthetic Customer {i}",
                "email": f"customer{i:03d}@example.test",
                "phone": f"+91-90000{i:05d}",
                "account_number": f"ACC{100000 + i}",
                "account_age": random.randint(30, 2400),
                "risk_level": "LOW",
            }
        )
    return customers


def generate_transactions(customers, n=1200, seed=42):
    random.seed(seed)
    rows = []
    now = datetime.now()
    txn_seq = 10000

    home_location = {c["customer_id"]: random.choice(LOCATIONS[:-1]) for c in customers}
    home_device = {c["customer_id"]: f"DEV{c['customer_id'][-3:]}" for c in customers}
    avg_amount = {c["customer_id"]: random.uniform(800, 4000) for c in customers}
    # CUST001 has a tight normal band for the viva demo.
    avg_amount["CUST001"] = 2000
    home_location["CUST001"] = "Hyderabad"
    home_device["CUST001"] = "DEV001"

    for i in range(n):
        customer = customers[i % len(customers)]
        cid = customer["customer_id"]
        txn_seq += 1
        is_fraud = random.random() < 0.12
        is_suspicious = (not is_fraud) and random.random() < 0.10

        ts = now - timedelta(days=random.randint(0, 45), hours=random.randint(0, 23), minutes=random.randint(0, 59))
        amount = max(50, random.gauss(avg_amount[cid], avg_amount[cid] * 0.35))
        location = home_location[cid]
        device = home_device[cid]
        intl = 0
        merchant = random.choice(MERCHANTS[:-1])

        if is_fraud:
            amount = random.uniform(25000, 120000)
            if random.random() < 0.6:
                location = random.choice(LOCATIONS[-2:] + INTL_LOCATIONS)
            if random.random() < 0.7:
                device = f"NEWDEV{random.randint(1000, 9999)}"
            if location in INTL_LOCATIONS:
                intl = 1
            merchant = random.choice(MERCHANTS)
        elif is_suspicious:
            amount = avg_amount[cid] * random.uniform(4, 8)
            if random.random() < 0.5:
                device = f"DEVX{random.randint(10, 99)}"
            if random.random() < 0.3:
                location = random.choice(LOCATIONS)

        if cid == "CUST001" and i < 40:
            is_fraud = False
            is_suspicious = False
            amount = random.uniform(500, 5000)
            location = "Hyderabad"
            device = "DEV001"
            intl = 0

        rows.append(
            {
                "transaction_id": f"TXN{txn_seq}",
                "customer_id": cid,
                "transaction_amount": round(amount, 2),
                "transaction_type": random.choice(TRANSACTION_TYPES),
                "transaction_time": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "merchant": merchant,
                "location": location,
                "device_id": device,
                "ip_address": _random_ip(),
                "payment_method": random.choice(PAYMENT_METHODS),
                "account_balance": round(amount + random.uniform(5000, 150000), 2),
                "transaction_frequency": random.randint(1, 8),
                "is_international": intl,
                "actual_label": 1 if is_fraud else 0,
            }
        )

    # Burst of rapid CUST001 transfers used in the sample workflow.
    burst_time = now - timedelta(minutes=30)
    for j in range(4):
        txn_seq += 1
        rows.append(
            {
                "transaction_id": f"TXN{txn_seq}",
                "customer_id": "CUST001",
                "transaction_amount": round(random.uniform(800, 2500), 2),
                "transaction_type": "TRANSFER",
                "transaction_time": (burst_time + timedelta(seconds=j * 25)).strftime("%Y-%m-%d %H:%M:%S"),
                "merchant": "Peer Transfer",
                "location": "Hyderabad",
                "device_id": "DEV001",
                "ip_address": "103.21.14.10",
                "payment_method": "UPI",
                "account_balance": 180000,
                "transaction_frequency": 5,
                "is_international": 0,
                "actual_label": 0,
            }
        )

    df = pd.DataFrame(rows)
    df = df.sort_values("transaction_time").reset_index(drop=True)
    return df


def write_csv(df, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def seed_users(conn):
    users = [
        ("admin", "admin@fraud.local", hash_password("Admin@123"), "ADMIN"),
        ("investigator", "investigator@fraud.local", hash_password("Invest@123"), "INVESTIGATOR"),
    ]
    conn.executemany(
        """
        INSERT OR IGNORE INTO users (username, email, password_hash, role)
        VALUES (?, ?, ?, ?)
        """,
        users,
    )


def seed_customers(conn, customers):
    conn.executemany(
        """
        INSERT OR REPLACE INTO customers
        (customer_id, name, email, phone, account_number, account_age, risk_level)
        VALUES (:customer_id, :name, :email, :phone, :account_number, :account_age, :risk_level)
        """,
        customers,
    )


def seed_transactions(conn, df):
    records = df.to_dict(orient="records")
    conn.executemany(
        """
        INSERT OR REPLACE INTO transactions (
            transaction_id, customer_id, transaction_amount, transaction_type,
            transaction_time, merchant, location, device_id, ip_address,
            payment_method, account_balance, transaction_frequency,
            is_international, actual_label
        ) VALUES (
            :transaction_id, :customer_id, :transaction_amount, :transaction_type,
            :transaction_time, :merchant, :location, :device_id, :ip_address,
            :payment_method, :account_balance, :transaction_frequency,
            :is_international, :actual_label
        )
        """,
        records,
    )


def seed(db_path=None, process=True):
    if db_path:
        Config.DATABASE_PATH = db_path
    init_db(db_path)
    customers = generate_customers()
    df = generate_transactions(customers)
    write_csv(df, ROOT / "data" / "raw" / "transactions.csv")
    write_csv(df.head(50), ROOT / "data" / "sample" / "sample_transactions.csv")

    conn = get_connection(db_path)
    try:
        seed_users(conn)
        seed_customers(conn, customers)
        seed_transactions(conn, df)
        conn.commit()
        logger.info("Seeded %s customers and %s transactions", len(customers), len(df))
    finally:
        conn.close()

    if process:
        from services.transaction_service import process_existing_transactions

        process_existing_transactions(db_path)
    return len(df)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-process", action="store_true", help="Skip fraud scoring after seed")
    args = parser.parse_args()
    count = seed(Config.DATABASE_PATH, process=not args.no_process)
    print(f"Seeded {count} synthetic transactions")


if __name__ == "__main__":
    main()
