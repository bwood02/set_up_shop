import sqlite3
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_recall_curve, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "shop.db"
MODELS_DIR = ROOT / "models"
MODELS_DIR.mkdir(exist_ok=True)


def main():
  conn = sqlite3.connect(DB_PATH)
  customers = pd.read_sql_query("SELECT * FROM customers", conn)
  orders = pd.read_sql_query("SELECT * FROM orders", conn)
  shipments = pd.read_sql_query("SELECT * FROM shipments", conn)
  order_items = pd.read_sql_query("SELECT * FROM order_items", conn)
  conn.close()

  shipments_agg = shipments.groupby("order_id", as_index=False).agg(
    promised_days=("promised_days", "max"),
    actual_days=("actual_days", "max"),
    late_delivery=("late_delivery", "max"),
  )
  item_agg = order_items.groupby("order_id", as_index=False).agg(
    item_count=("order_item_id", "count"),
    quantity_sum=("quantity", "sum"),
  )

  df = (
    orders.merge(customers, on="customer_id", how="left")
    .merge(shipments_agg, on="order_id", how="left")
    .merge(item_agg, on="order_id", how="left")
  )

  for col in ["order_datetime", "birthdate", "created_at"]:
    dt = pd.to_datetime(df[col], errors="coerce")
    df[f"{col}_year"] = dt.dt.year
    df[f"{col}_month"] = dt.dt.month
    df[f"{col}_dow"] = dt.dt.dayofweek

  birth = pd.to_datetime(df["birthdate"], errors="coerce")
  order_dt = pd.to_datetime(df["order_datetime"], errors="coerce")
  df["customer_age"] = (order_dt - birth).dt.days / 365.25
  df["delivery_delay_days"] = df["actual_days"] - df["promised_days"]

  target = "is_fraud"
  exclude = {
    target,
    "order_id",
    "ship_datetime",
    "full_name",
    "email",
    "promo_code",
    "order_datetime",
    "birthdate",
    "created_at",
  }
  features = [c for c in df.columns if c not in exclude]
  X = df[features].copy()
  y = df[target].astype(int)

  numeric_features = X.select_dtypes(include=[np.number]).columns.tolist()
  categorical_features = [c for c in X.columns if c not in numeric_features]

  X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
  )

  preprocessor = ColumnTransformer(
    transformers=[
      (
        "num",
        Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]),
        numeric_features,
      ),
      (
        "cat",
        Pipeline(
          [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
          ]
        ),
        categorical_features,
      ),
    ]
  )

  models = {
    "logistic": LogisticRegression(max_iter=1500, class_weight="balanced"),
    "random_forest": RandomForestClassifier(
      n_estimators=300, random_state=42, class_weight="balanced_subsample"
    ),
    "gradient_boosting": GradientBoostingClassifier(random_state=42),
  }

  cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
  best_name = None
  best_auc = -1.0
  for name, model in models.items():
    pipe = Pipeline([("prep", preprocessor), ("model", model)])
    auc = cross_val_score(pipe, X_train, y_train, cv=cv, scoring="roc_auc", n_jobs=-1).mean()
    if auc > best_auc:
      best_name, best_auc = name, auc

  best_model = Pipeline([("prep", preprocessor), ("model", models[best_name])])
  best_model.fit(X_train, y_train)
  y_proba = best_model.predict_proba(X_test)[:, 1]
  roc = roc_auc_score(y_test, y_proba)

  precision, recall, thresholds = precision_recall_curve(y_test, y_proba)
  f1_vals = 2 * (precision * recall) / (precision + recall + 1e-9)
  idx = int(np.nanargmax(f1_vals))
  threshold = float(thresholds[max(idx - 1, 0)]) if len(thresholds) else 0.5
  y_pred = (y_proba >= threshold).astype(int)
  f1 = f1_score(y_test, y_pred, zero_division=0)

  artifact = {
    "pipeline": best_model,
    "threshold": threshold,
    "features": features,
    "model_name": best_name,
  }
  output_path = MODELS_DIR / "fraud_model.joblib"
  joblib.dump(artifact, output_path)
  print(f"Selected model: {best_name}")
  print(f"ROC-AUC: {roc:.4f}")
  print(f"F1 @ threshold {threshold:.4f}: {f1:.4f}")
  print(f"Saved artifact: {output_path}")


if __name__ == "__main__":
  main()
