# AI-Powered Real-Time Financial Fraud Detection

Local Flask application that scores **new financial transactions** with a hybrid pipeline:

- Machine learning fraud probability (50%)
- Rule-based risk (30%)
- User-behavior anomaly scoring from SQLite history (20%)

Every submitted transaction is **inserted as a new SQLite row**, analyzed independently, and retained in history. High-risk transactions open an investigation, evidence pack, timeline, and alert. Medium-risk transactions require a demo OTP.

This project uses **synthetic demo data only**. It is not connected to a bank.

## Setup (Windows)

```bat
python --version
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python seed.py
python train_model.py
pytest -q
python app.py
```

Open http://127.0.0.1:5000

## Demo accounts

| Role | Email | Password |
| --- | --- | --- |
| USER | user@example.com | Password@123 |
| INVESTIGATOR | investigator@example.com | Password@123 |
| ADMIN | admin@example.com | Password@123 |

## New transaction flow

1. Log in
2. Open **New Transaction**
3. Enter details and click **Analyze Transaction**
4. Review ML / rule / behavior / final scores
5. Continue submitting unlimited additional transactions; history and dashboards update from the database

## Risk bands

- 0–30 LOW → AUTO_APPROVED
- 31–70 MEDIUM → ADDITIONAL_VERIFICATION (OTP, 2 minutes, demo code shown)
- 71–100 HIGH → UNDER_INVESTIGATION (alert + evidence + timeline)

Set `SECRET_KEY` in the environment for non-dev use.
