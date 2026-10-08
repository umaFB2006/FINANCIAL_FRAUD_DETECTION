PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('ADMIN', 'INVESTIGATOR')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    account_number TEXT UNIQUE,
    account_age INTEGER DEFAULT 0,
    risk_level TEXT DEFAULT 'LOW',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    transaction_amount REAL NOT NULL,
    transaction_type TEXT NOT NULL,
    transaction_time TEXT NOT NULL,
    merchant TEXT,
    location TEXT,
    device_id TEXT,
    ip_address TEXT,
    payment_method TEXT,
    account_balance REAL,
    transaction_frequency INTEGER DEFAULT 0,
    is_international INTEGER DEFAULT 0,
    actual_label INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS fraud_predictions (
    prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id TEXT NOT NULL,
    fraud_probability REAL NOT NULL,
    risk_score REAL NOT NULL,
    prediction TEXT NOT NULL,
    model_name TEXT,
    prediction_time TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id)
);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id TEXT PRIMARY KEY,
    transaction_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    alert_message TEXT,
    status TEXT NOT NULL DEFAULT 'OPEN',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id)
);

CREATE TABLE IF NOT EXISTS investigations (
    investigation_id TEXT PRIMARY KEY,
    transaction_id TEXT NOT NULL,
    alert_id TEXT,
    investigator TEXT,
    case_status TEXT NOT NULL DEFAULT 'OPEN',
    investigation_summary TEXT,
    evidence TEXT,
    recommendation TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id),
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id)
);

CREATE TABLE IF NOT EXISTS investigation_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    investigation_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    description TEXT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (investigation_id) REFERENCES investigations(investigation_id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    entity TEXT,
    entity_id TEXT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_txn_time ON transactions(transaction_time);
CREATE INDEX IF NOT EXISTS idx_txn_customer_time ON transactions(customer_id, transaction_time);
CREATE INDEX IF NOT EXISTS idx_pred_txn ON fraud_predictions(transaction_id);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status, severity, created_at);
CREATE INDEX IF NOT EXISTS idx_inv_status ON investigations(case_status, created_at);
