import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SQLITE_DB = ROOT / "shop.db"
OUTPUT_SQL = ROOT / "web" / "supabase" / "seed.sql"


def sql_value(value):
  if value is None:
    return "NULL"
  if isinstance(value, (int, float)):
    return str(value)
  text = str(value).replace("'", "''")
  return f"'{text}'"


def emit_table_inserts(cursor, table_name: str, columns: list[str]) -> str:
  rows = cursor.execute(f"select {', '.join(columns)} from {table_name}").fetchall()
  if not rows:
    return ""
  values_sql = []
  for row in rows:
    values_sql.append("(" + ", ".join(sql_value(v) for v in row) + ")")
  return (
    f"insert into public.{table_name} ({', '.join(columns)}) values\n"
    + ",\n".join(values_sql)
    + ";\n"
  )


def main():
  if not SQLITE_DB.exists():
    raise FileNotFoundError(f"Could not find SQLite file: {SQLITE_DB}")

  conn = sqlite3.connect(SQLITE_DB)
  cur = conn.cursor()

  customers_cols = [
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
  ]
  orders_cols = [
    "order_id",
    "customer_id",
    "order_datetime",
    "billing_zip",
    "shipping_zip",
    "shipping_state",
    "payment_method",
    "device_type",
    "ip_country",
    "promo_used",
    "promo_code",
    "order_subtotal",
    "shipping_fee",
    "tax_amount",
    "order_total",
    "risk_score",
    "is_fraud",
  ]
  shipments_cols = [
    "shipment_id",
    "order_id",
    "ship_datetime",
    "carrier",
    "shipping_method",
    "distance_band",
    "promised_days",
    "actual_days",
    "late_delivery",
  ]

  sql_parts = [
    "-- Generated from shop.db for Supabase Postgres",
    "begin;",
    "truncate table public.order_scores restart identity;",
    "truncate table public.scoring_runs restart identity;",
    "truncate table public.shipments restart identity cascade;",
    "truncate table public.orders restart identity cascade;",
    "truncate table public.customers restart identity cascade;",
    emit_table_inserts(cur, "customers", customers_cols),
    emit_table_inserts(cur, "orders", orders_cols),
    emit_table_inserts(cur, "shipments", shipments_cols),
    "commit;",
    "",
  ]

  OUTPUT_SQL.parent.mkdir(parents=True, exist_ok=True)
  OUTPUT_SQL.write_text("\n".join(sql_parts), encoding="utf-8")
  conn.close()
  print(f"Wrote {OUTPUT_SQL}")


if __name__ == "__main__":
  main()
