# Fraud inference API

FastAPI service that loads `models/fraud_model.joblib` and exposes `POST /predict`.

## Environment

- `FRAUD_MODEL_PATH` — path to joblib (default: repo `models/fraud_model.joblib`)
- `FRAUD_API_SECRET` — optional; when set, require header `X-Fraud-Api-Secret` on `/predict`

## Local

From repo root:

```bash
pip install -r fraud-api/requirements.txt
set FRAUD_API_SECRET=your_secret
uvicorn fraud-api.main:app --reload --port 8080
```

On Windows PowerShell, run uvicorn with module path:

```powershell
$env:PYTHONPATH="."
uvicorn fraud-api.main:app --host 127.0.0.1 --port 8080
```

## Docker

From repo root:

```bash
docker build -f fraud-api/Dockerfile -t shop-fraud-api .
docker run -p 8080:8080 -e FRAUD_API_SECRET=your_secret shop-fraud-api
```

## Request

`POST /predict`

```json
{
  "order": { "order_id": 1, "customer_id": 1, ... },
  "customer": { "customer_id": 1, "gender": "M", ... }
}
```

Keys must match Supabase column names (snake_case).
