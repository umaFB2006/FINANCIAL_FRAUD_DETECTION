# Architecture

```
USER
  → WEB DASHBOARD (templates + Chart.js polling)
    → FLASK API (api/*)
      → TRANSACTION VALIDATION
      → PREPROCESSING / FEATURE ENGINEERING
      → ML FRAUD MODEL (joblib)
      → ISOLATION FOREST
      → RULE ENGINE
      → RISK ENGINE (weighted combination)
      → EXPLAINABLE AI
      → ALERT ENGINE
      → AUTONOMOUS INVESTIGATION (simulation)
      → CASE MANAGEMENT
      → SQLITE
      → INVESTIGATOR DASHBOARD
```

`database/database.py` is the only persistence adapter. Replacing it with SQLAlchemy + PostgreSQL later does not require rewriting the UI.

IBM calls live in `services/ibm_integration.py` and are off by default.
