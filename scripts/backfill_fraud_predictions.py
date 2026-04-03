"""
Backfill fraud predictions for historical orders in Supabase.

Writes:
  - orders.fraud_probability
  - orders.predicted_fraud
  - orders.fraud_scored_at

This is intended to be run server-side with a DATABASE_URL that can read/write
using your Supabase service role (recommended).
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote

from fraud_ml_common import align_feature_matrix, build_training_dataframe


REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = REPO_ROOT / "models"
MODEL_PATH = MODELS_DIR / "fraud_model.joblib"


_SUPABASE_AUTH_SPLIT_MARKERS = ("@db.", "@aws-")


def _clean_env_str(value: str) -> str:
    return value.strip().strip("\ufeff")


def encode_database_url_password(url: str) -> str:
    """
    If the password contains a raw '@', SQLAlchemy's URL parsing can treat it as
    the separator between userinfo and host. Encode those '@' (and other
    reserved chars) in the password.

    Matches the approach used in `scripts/train_fraud_model.py`.
    """
    if "://" not in url:
        return url
    scheme, sep, rest = url.partition("://")

    marker_pos = -1
    for m in _SUPABASE_AUTH_SPLIT_MARKERS:
        p = rest.rfind(m)
        if p > marker_pos:
            marker_pos = p

    if marker_pos == -1:
        return url

    userinfo, host_part = rest[:marker_pos], rest[marker_pos:]
    if ":" not in userinfo:
        return url

    username, _, password = userinfo.partition(":")
    if "@" not in password:
        return url

    safe = quote(password, safe="")
    return f"{scheme}{sep}{username}:{safe}{host_part}"


def _ensure_sslmode_require(url: str) -> str:
    lower = url.lower()
    if "sslmode=" in lower:
        return url
    joiner = "&" if "?" in url else "?"
    return f"{url}{joiner}sslmode=require"


def resolve_database_url() -> str:
    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not url:
        raise RuntimeError(
            "Missing DATABASE_URL (or SUPABASE_DB_URL). "
            "Set it in your shell or in the repo root .env before running."
        )
    url = _clean_env_str(url)
    url = encode_database_url_password(url)
    return _ensure_sslmode_require(url)


def load_table_or_empty_df(engine, sql, columns: list[str]) -> pd.DataFrame:
    try:
        return pd.read_sql_query(text(sql), engine)
    except Exception:
        # Some deployments might not have order_items; keep pipeline running.
        return pd.DataFrame(columns=columns)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Max number of orders to backfill (0 = all).")
    parser.add_argument("--batch-size", type=int, default=250, help="Batch size for processing orders.")
    parser.add_argument("--dry-run", action="store_true", help="Compute scores but do not update Supabase.")
    args = parser.parse_args()

    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Fraud model artifact not found at: {MODEL_PATH}")

    db_url = resolve_database_url()
    engine = create_engine(db_url, connect_args={"connect_timeout": 20})

    art = joblib.load(MODEL_PATH)
    pipeline = art["pipeline"]
    threshold = float(art["threshold"])
    expected_features = list(art["features"])

    update_ts = datetime.now(timezone.utc).isoformat()

    # Pick orders that haven't been scored yet.
    order_limit_clause = "" if args.limit <= 0 else f"LIMIT {int(args.limit)}"
    orders_query = f"""
      SELECT
        order_id, customer_id, order_datetime,
        billing_zip, shipping_zip, shipping_state,
        payment_method, device_type, ip_country,
        promo_used, promo_code,
        order_subtotal, shipping_fee, tax_amount, order_total,
        risk_score,
        is_fraud
      FROM public.orders
      WHERE fraud_probability IS NULL OR predicted_fraud IS NULL
      ORDER BY order_id
      {order_limit_clause}
    """

    all_orders = pd.read_sql_query(text(orders_query), engine)
    if all_orders.empty:
        print("No orders found to backfill.")
        return

    order_ids = all_orders["order_id"].astype(int).tolist()
    print(f"Found {len(order_ids)} orders to backfill.")

    scored = 0
    for start in range(0, len(order_ids), args.batch_size):
        batch_ids = order_ids[start : start + args.batch_size]

        in_clause = "(" + ",".join(str(int(x)) for x in batch_ids) + ")"

        orders_batch = all_orders[all_orders["order_id"].isin(batch_ids)].copy()

        customers_query = f"""
          SELECT
            customer_id, full_name, email, gender, birthdate, created_at,
            city, state, zip_code, customer_segment, loyalty_tier, is_active
          FROM public.customers
          WHERE customer_id IN (SELECT DISTINCT customer_id FROM public.orders WHERE order_id IN {in_clause})
        """

        shipments_query = f"""
          SELECT
            order_id, promised_days, actual_days, late_delivery
          FROM public.shipments
          WHERE order_id IN {in_clause}
        """

        # order_items isn't included in your checked-in `schema.sql`,
        # so tolerate it being missing.
        order_items_query = f"""
          SELECT
            order_item_id, order_id, quantity
          FROM public.order_items
          WHERE order_id IN {in_clause}
        """

        customers = load_table_or_empty_df(
            engine,
            customers_query,
            columns=[
                "customer_id",
                "full_name",
                "email",
                "gender",
                "birthdate",
                "created_at",
                "city",
                "state",
                "zip_code",
                "customer_segment",
                "loyalty_tier",
                "is_active",
            ],
        )
        shipments = load_table_or_empty_df(engine, shipments_query, columns=["order_id", "promised_days", "actual_days", "late_delivery"])
        order_items = load_table_or_empty_df(
            engine,
            order_items_query,
            columns=["order_item_id", "order_id", "quantity"],
        )

        df, _, _ = build_training_dataframe(
            orders_batch,
            customers,
            shipments,
            order_items,
        )

        # Align to the exact feature order used by the training artifact.
        X = align_feature_matrix(df[expected_features] if set(expected_features).issubset(df.columns) else df, expected_features)

        proba = pipeline.predict_proba(X)[:, 1]
        predicted = (proba >= threshold).astype(int)

        if args.dry_run:
            for oid, p, pred in zip(batch_ids, proba, predicted):
                print(f"[dry-run] order_id={oid} fraud_probability={float(p):.6f} predicted_fraud={int(pred)}")
            continue

        update_sql = text(
            """
            UPDATE public.orders
            SET fraud_probability = :prob,
                predicted_fraud = :pred,
                fraud_scored_at = :ts
            WHERE order_id = :order_id
            """
        )

        params = []
        for oid, p, pred in zip(batch_ids, proba, predicted):
            params.append(
                {
                    "order_id": int(oid),
                    "prob": float(p),
                    "pred": int(pred),
                    "ts": update_ts,
                }
            )

        with engine.begin() as conn:
            conn.execute(update_sql, params)

        scored += len(batch_ids)
        print(f"Backfilled {scored}/{len(order_ids)} orders...")

    print("Backfill complete.")


if __name__ == "__main__":
    main()

