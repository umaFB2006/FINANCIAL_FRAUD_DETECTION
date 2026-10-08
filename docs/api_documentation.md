# API documentation

All JSON APIs return `{ "success": true, "data": ... }` or `{ "success": false, "error": "..." }`.

Session cookie authentication is required except for `POST /api/auth/login` and the HTML login page.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login` | `{username, password}` |
| POST | `/api/auth/logout` | End session |
| POST | `/api/transactions` | Validate, store, score, alert, maybe investigate |
| GET | `/api/transactions` | `q`, `prediction`, `page`, `per_page` |
| GET | `/api/transactions/<id>` | Detail |
| POST | `/api/fraud/predict` | Score without persisting unless `persist: true` |
| GET | `/api/alerts` | `severity`, `status` |
| GET | `/api/alerts/<id>` | Alert detail |
| GET | `/api/investigations` | `status` |
| GET | `/api/investigations/<id>` | Full case |
| POST | `/api/investigations/<id>/update` | `case_status`, `notes`, `final_decision` |
| GET | `/api/dashboard/stats` | KPI cards + latest rows |
| GET | `/api/dashboard/charts` | Chart.js datasets |
| GET | `/api/reports/fraud` | `period=daily\|weekly\|monthly`, `format=csv` |
| GET | `/api/reports/investigations` | `format=csv` |
| GET | `/api/reports/customers` | Customer risk CSV/JSON |

### Sample intake body

```json
{
  "customer_id": "CUST001",
  "amount": 75000,
  "transaction_type": "TRANSFER",
  "merchant": "Example Merchant",
  "location": "New Delhi",
  "device_id": "NEWDEVICE99",
  "ip_address": "192.168.1.10",
  "payment_method": "UPI",
  "account_balance": 100000,
  "is_international": false
}
```

HTTP errors: 400 validation, 401 unauthenticated, 403 forbidden, 404 missing, 500 unexpected.
