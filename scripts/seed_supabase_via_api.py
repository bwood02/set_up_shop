import json
import os
import sqlite3
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "shop.db"
BATCH_SIZE = 250


def require_env(name: str) -> str:
  value = os.getenv(name)
  if not value:
    raise RuntimeError(f"Missing required env var: {name}")
  return value


def fetch_rows(conn: sqlite3.Connection, table: str) -> list[dict]:
  conn.row_factory = sqlite3.Row
  rows = conn.execute(f"select * from {table}").fetchall()
  return [dict(r) for r in rows]


def chunked(items: list[dict], size: int):
  for i in range(0, len(items), size):
    yield items[i : i + size]


def post_upsert(base_url: str, key: str, table: str, rows: list[dict], conflict_col: str):
  if not rows:
    return
  url = f"{base_url}/rest/v1/{table}?on_conflict={urllib.parse.quote(conflict_col)}"
  headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates,return=minimal",
  }

  for idx, batch in enumerate(chunked(rows, BATCH_SIZE), start=1):
    req = urllib.request.Request(
      url=url,
      data=json.dumps(batch).encode("utf-8"),
      headers=headers,
      method="POST",
    )
    with urllib.request.urlopen(req) as resp:
      if resp.status >= 300:
        raise RuntimeError(f"Failed on {table} batch {idx} with status {resp.status}")
    print(f"{table}: upserted batch {idx} ({len(batch)} rows)")


def main():
  supabase_url = require_env("SUPABASE_URL").rstrip("/")
  service_role_key = require_env("SUPABASE_SERVICE_ROLE_KEY")

  if not DB_PATH.exists():
    raise FileNotFoundError(f"Missing SQLite DB at {DB_PATH}")

  conn = sqlite3.connect(DB_PATH)
  customers = fetch_rows(conn, "customers")
  orders = fetch_rows(conn, "orders")
  shipments = fetch_rows(conn, "shipments")
  conn.close()

  print(f"customers rows: {len(customers)}")
  print(f"orders rows: {len(orders)}")
  print(f"shipments rows: {len(shipments)}")

  # Keep FK-safe order.
  post_upsert(supabase_url, service_role_key, "customers", customers, "customer_id")
  post_upsert(supabase_url, service_role_key, "orders", orders, "order_id")
  post_upsert(supabase_url, service_role_key, "shipments", shipments, "shipment_id")

  print("Seeding completed.")


if __name__ == "__main__":
  main()
