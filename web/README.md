This is a [Next.js](https://nextjs.org) app for your Shop INTEX Chapter 17 prep project.

## Getting Started

1) Install packages and create local env:

```bash
npm install
cp .env.example .env.local
```

2) Fill in `.env.local`:

```bash
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
```

3) Start dev server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Assignment features included

- Select Customer page at `/`
- Customer dashboard + order history at `/customer/[id]`
- Place new order form at `/customer/[id]/new-order`
- Warehouse queue page at `/warehouse`
- Run scoring button (POST) at `/api/scoring/run`
- Order create endpoint (POST) at `/api/orders`
- Pipeline prediction output list shown on `/warehouse`

## Data layer architecture

- Repository contract: `src/lib/shop-repository.ts`
- Supabase implementation: `src/lib/supabase-shop-repository.ts`
- Local fallback implementation: `src/lib/memory-shop-repository.ts`
- Existing in-memory mock store remains in `src/lib/shop-store.ts` as fallback if Supabase env vars are missing.

## Supabase setup + `shop.db` seed

1) In Supabase SQL editor, run:
- `supabase/schema.sql`

2) Fastest seed path (recommended): run API batch seeder from project root:

```bash
python scripts/seed_supabase_via_api.py
```

This script reads local `shop.db` and upserts `customers`, `orders`, and `shipments` into Supabase.

Alternative (SQL-based) if needed:
- Generate SQL: `python scripts/generate_supabase_seed_sql.py`
- Run: `supabase/seed.sql` (or `supabase/seed_chunks/*` if SQL Editor size limits are hit)

## Deploy on Vercel

1) Push repo to GitHub and import in Vercel.
2) Set project root to `web`.
3) Add env vars in Vercel:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
4) Deploy and verify:
- `/` Select Customer list loads
- `/customer/[id]` dashboard + order history load
- New order save returns to dashboard and persists
- `/warehouse` queue displays top 50
- `Run Scoring` updates queue + prediction output section

## Notes

- If notebook files fail to open in Cursor due webview/service-worker errors, use VS Code + Jupyter for notebook execution/submission.
- For this assignment, `Run Scoring` is deterministic given the same order data, so repeated runs can produce the same queue until data changes.

## Fraud model (live inference)

- Train: `python scripts/train_fraud_model.py` (set `DATABASE_URL` or use local `shop.db`).
- Inference: deploy [`fraud-api`](../fraud-api/) (see [`fraud-api/README.md`](../fraud-api/README.md)).
- Set `FRAUD_API_URL` and optional `FRAUD_API_SECRET` in Vercel; new orders call `/predict` and fill `fraud_probability` / `predicted_fraud` on `orders`.
- Run [`web/supabase/migrations/001_fraud_prediction_columns.sql`](supabase/migrations/001_fraud_prediction_columns.sql) in Supabase if the table predates those columns.

## Nightly retrain (GitHub Actions)

- Add repo secret `DATABASE_URL` (Supabase Postgres connection string).
- Workflow [`.github/workflows/nightly-retrain.yml`](../../.github/workflows/nightly-retrain.yml) uploads `fraud_model.joblib` as an artifact; redeploy or copy into `fraud-api` / `models/` as needed.
