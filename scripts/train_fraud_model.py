import os
import sqlite3
import sys
from pathlib import Path
from urllib.parse import quote
import socket

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))
load_dotenv(_ROOT / ".env", encoding="utf-8-sig")

import joblib
import numpy as np
import pandas as pd
from fraud_ml_common import build_training_dataframe
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_recall_curve, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = _ROOT
DB_PATH = ROOT / "shop.db"
MODELS_DIR = ROOT / "models"
MODELS_DIR.mkdir(exist_ok=True)

# Host markers after user:password (Supabase direct + common pooler hostname).
_SUPABASE_AUTH_SPLIT_MARKERS = ("@db.", "@aws-")


def _clean_env_str(value: str) -> str:
    s = value.strip().strip("\ufeff")
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        s = s[1:-1]
    return s.strip()


def encode_database_url_password(url: str) -> str:
    """If the password contains a raw '@', urlparse/SQLAlchemy treat it wrong. Encode those chars.

    Paste the normal Supabase URI with a real password; no need to pre-encode in .env or GitHub.
    Already-encoded passwords (no raw '@' in the secret) are left unchanged.
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


def resolve_postgres_connection_url() -> str:
    """Database URL from DATABASE_URL or discrete SUPABASE_DB_* vars (recommended if URL keeps breaking)."""
    from sqlalchemy.engine.url import URL

    host = os.getenv("SUPABASE_DB_HOST")
    password = os.getenv("SUPABASE_DB_PASSWORD")
    if host and password:
        host = _clean_env_str(host)
        password = _clean_env_str(password)
        user = _clean_env_str(os.getenv("SUPABASE_DB_USER", "postgres"))
        dbname = _clean_env_str(os.getenv("SUPABASE_DB_NAME", "postgres"))
        port = int(_clean_env_str(os.getenv("SUPABASE_DB_PORT", "5432")))
        u = URL.create(
            drivername="postgresql+psycopg2",
            username=user,
            password=password,
            host=host,
            port=port,
            database=dbname,
            query={"sslmode": "require"},
        )
        return u.render_as_string(hide_password=False)

    raw = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not raw:
        return ""
    url = encode_database_url_password(_clean_env_str(raw))
    return _ensure_sslmode_require(url)


def load_tables_sqlite() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    conn = sqlite3.connect(DB_PATH)
    customers = pd.read_sql_query("SELECT * FROM customers", conn)
    orders = pd.read_sql_query("SELECT * FROM orders", conn)
    shipments = pd.read_sql_query("SELECT * FROM shipments", conn)
    order_items = pd.read_sql_query("SELECT * FROM order_items", conn)
    conn.close()
    return customers, orders, shipments, order_items


def load_tables_postgres(url: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    try:
        from sqlalchemy import create_engine, text
    except ImportError as exc:
        raise RuntimeError("Install sqlalchemy for DATABASE_URL training: pip install sqlalchemy psycopg2-binary") from exc
    # GitHub runners may have IPv6 routing issues; force IPv4 by resolving host
    # to an IPv4 address and passing it as `hostaddr` to psycopg2.
    connect_args: dict[str, object] = {"connect_timeout": 20}
    hostaddr = None
    try:
        from sqlalchemy.engine.url import make_url
        u = make_url(url)
        host = u.host
        port = u.port or 5432
        if host:
            infos = socket.getaddrinfo(host, port, family=socket.AF_INET, type=socket.SOCK_STREAM)
            if infos:
                hostaddr = infos[0][4][0]
                connect_args["hostaddr"] = hostaddr
    except Exception:
        pass
    print(f"[train] Supabase hostaddr_ipv4={hostaddr}")

    engine = create_engine(url, connect_args=connect_args)
    try:
        customers = pd.read_sql_query(text("SELECT * FROM customers"), engine)
        orders = pd.read_sql_query(text("SELECT * FROM orders"), engine)
        shipments = pd.read_sql_query(text("SELECT * FROM shipments"), engine)
        try:
            order_items = pd.read_sql_query(text("SELECT * FROM order_items"), engine)
        except Exception:
            order_items = pd.DataFrame(columns=["order_item_id", "order_id", "quantity"])
        return customers, orders, shipments, order_items
    finally:
        engine.dispose()


def main() -> None:
    db_url = resolve_postgres_connection_url()
    if db_url:
        try:
            customers, orders, shipments, order_items = load_tables_postgres(db_url)
        except Exception as exc:
            msg = str(exc).lower()
            if "name or service not known" in msg or "could not translate host name" in msg:
                raise ConnectionError(
                    "Could not reach the database host (DNS/network). Check:\n"
                    "  • Phone or school Wi-Fi sometimes blocks database domains — try another network or phone hotspot.\n"
                    "  • In Supabase: Project Settings -> Database — copy **Host** again (must be like db.xxxxx.supabase.co).\n"
                    "  • In PowerShell: nslookup db.YOUR_REF.supabase.co should return an address.\n"
                    "  • Or set discrete vars in .env (no URL parsing): SUPABASE_DB_HOST, SUPABASE_DB_PASSWORD, "
                    "optional SUPABASE_DB_USER, SUPABASE_DB_PORT, SUPABASE_DB_NAME.\n"
                    f"Original error: {exc}"
                ) from exc
            raise
    elif DB_PATH.exists():
        customers, orders, shipments, order_items = load_tables_sqlite()
    else:
        raise FileNotFoundError(f"No DATABASE_URL and no SQLite at {DB_PATH}")

    df, features, y = build_training_dataframe(orders, customers, shipments, order_items)
    if y is None:
        raise RuntimeError("Training data must include is_fraud on orders")

    X = df[features].copy()

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
