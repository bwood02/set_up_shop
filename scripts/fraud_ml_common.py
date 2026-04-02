"""
Shared feature engineering for fraud training and inference.
Checkout-time inference uses neutral defaults for shipment / order_item aggregates.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TARGET = "is_fraud"
EXCLUDE_FROM_FEATURES = {
    TARGET,
    "order_id",
    "ship_datetime",
    "full_name",
    "email",
    "promo_code",
    "order_datetime",
    "birthdate",
    "created_at",
}


def merge_frames(
    orders: pd.DataFrame,
    customers: pd.DataFrame,
    shipments_agg: pd.DataFrame,
    item_agg: pd.DataFrame,
) -> pd.DataFrame:
    return (
        orders.merge(customers, on="customer_id", how="left")
        .merge(shipments_agg, on="order_id", how="left")
        .merge(item_agg, on="order_id", how="left")
    )


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ["order_datetime", "birthdate", "created_at"]:
        if col not in out.columns:
            continue
        dt = pd.to_datetime(out[col], errors="coerce")
        out[f"{col}_year"] = dt.dt.year
        out[f"{col}_month"] = dt.dt.month
        out[f"{col}_dow"] = dt.dt.dayofweek

    if "birthdate" in out.columns and "order_datetime" in out.columns:
        birth = pd.to_datetime(out["birthdate"], errors="coerce")
        order_dt = pd.to_datetime(out["order_datetime"], errors="coerce")
        out["customer_age"] = (order_dt - birth).dt.days / 365.25

    if "actual_days" in out.columns and "promised_days" in out.columns:
        out["delivery_delay_days"] = out["actual_days"] - out["promised_days"]
    return out


def shipments_and_items_from_db(
    shipment_df: pd.DataFrame, order_items_df: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    shipments_agg = shipment_df.groupby("order_id", as_index=False).agg(
        promised_days=("promised_days", "max"),
        actual_days=("actual_days", "max"),
        late_delivery=("late_delivery", "max"),
    )
    item_agg = order_items_df.groupby("order_id", as_index=False).agg(
        item_count=("order_item_id", "count"),
        quantity_sum=("quantity", "sum"),
    )
    return shipments_agg, item_agg


def build_training_dataframe(
    orders: pd.DataFrame,
    customers: pd.DataFrame,
    shipment_df: pd.DataFrame,
    order_items_df: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str], pd.Series | None]:
    shipments_agg, item_agg = shipments_and_items_from_db(shipment_df, order_items_df)
    df = merge_frames(orders, customers, shipments_agg, item_agg)
    df = engineer_features(df)
    features = [c for c in df.columns if c not in EXCLUDE_FROM_FEATURES]
    y = df[TARGET].astype(int) if TARGET in df.columns else None
    return df, features, y


def align_feature_matrix(X: pd.DataFrame, feature_names: list[str]) -> pd.DataFrame:
    out = pd.DataFrame(index=X.index)
    for col in feature_names:
        out[col] = X[col] if col in X.columns else np.nan
    return out


def build_single_prediction_frame(order: dict, customer: dict) -> tuple[pd.DataFrame, list[str]]:
    order_id = order.get("order_id")
    orders = pd.DataFrame([order])
    customers = pd.DataFrame([customer])
    shipments_agg = pd.DataFrame(
        [
            {
                "order_id": order_id,
                "promised_days": np.nan,
                "actual_days": np.nan,
                "late_delivery": np.nan,
            }
        ]
    )
    item_agg = pd.DataFrame(
        [{"order_id": order_id, "item_count": 0, "quantity_sum": 0}]
    )
    df = merge_frames(orders, customers, shipments_agg, item_agg)
    df = engineer_features(df)
    features = [c for c in df.columns if c not in EXCLUDE_FROM_FEATURES]
    X = df[features].copy()
    return X, features
