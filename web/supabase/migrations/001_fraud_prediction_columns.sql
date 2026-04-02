-- Run in Supabase SQL Editor if not using a migration runner.
-- Adds model prediction outputs; keep is_fraud as historical/ground-truth when present.

alter table public.orders add column if not exists fraud_probability double precision;
alter table public.orders add column if not exists predicted_fraud integer;
alter table public.orders add column if not exists fraud_scored_at timestamptz;
