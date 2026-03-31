from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = ROOT / "web" / "supabase" / "seed.sql"
OUT_DIR = ROOT / "web" / "supabase" / "seed_chunks"


def write_chunk(path: Path, content: str) -> None:
  path.write_text(content.strip() + "\n", encoding="utf-8")
  print(f"Wrote {path}")


def split_values_tuples(values_blob: str) -> list[str]:
  tuples: list[str] = []
  start = None
  depth = 0
  in_string = False
  i = 0
  while i < len(values_blob):
    ch = values_blob[i]
    if ch == "'":
      # Handle escaped single-quote in SQL literal ('')
      if i + 1 < len(values_blob) and values_blob[i + 1] == "'":
        i += 2
        continue
      in_string = not in_string
    elif not in_string:
      if ch == "(":
        if depth == 0:
          start = i
        depth += 1
      elif ch == ")":
        depth -= 1
        if depth == 0 and start is not None:
          tuples.append(values_blob[start : i + 1].strip())
          start = None
    i += 1
  return tuples


def split_insert_statement(insert_sql: str, rows_per_chunk: int) -> list[str]:
  values_idx = insert_sql.lower().find(" values")
  if values_idx == -1:
    return [insert_sql]
  header = insert_sql[: values_idx + len(" values")].strip()
  values_blob = insert_sql[values_idx + len(" values") :].strip()
  if values_blob.endswith(";"):
    values_blob = values_blob[:-1]
  tuples = split_values_tuples(values_blob)
  if not tuples:
    return [insert_sql]

  chunks: list[str] = []
  for i in range(0, len(tuples), rows_per_chunk):
    block = tuples[i : i + rows_per_chunk]
    chunk_sql = header + "\n" + ",\n".join(block) + ";\n"
    chunks.append(chunk_sql)
  return chunks


def main() -> None:
  sql = SEED_PATH.read_text(encoding="utf-8")
  OUT_DIR.mkdir(parents=True, exist_ok=True)

  reset_match = re.search(
    r"begin;\s*.*?truncate table public\.customers restart identity cascade;\s*",
    sql,
    flags=re.IGNORECASE | re.DOTALL,
  )
  if not reset_match:
    raise RuntimeError("Could not find reset/truncate block in seed.sql")

  reset_sql = (
    "-- Reset block (run once)\n"
    + reset_match.group(0)
    + "\ncommit;\n"
  )
  write_chunk(OUT_DIR / "00_reset.sql", reset_sql)

  # Extract each INSERT statement as a standalone chunk.
  insert_pattern = re.compile(
    r"insert into public\.(customers|orders|shipments)\s*\(.*?;",
    flags=re.IGNORECASE | re.DOTALL,
  )
  inserts = list(insert_pattern.finditer(sql))
  if not inserts:
    raise RuntimeError("No INSERT statements found in seed.sql")

  table_counts = {"customers": 0, "orders": 0, "shipments": 0}
  rows_per_table = {"customers": 250, "orders": 150, "shipments": 150}
  for idx, match in enumerate(inserts, start=1):
    table = match.group(1).lower()
    insert_sql = match.group(0).strip()
    split_chunks = split_insert_statement(insert_sql, rows_per_table[table])
    for chunk_sql in split_chunks:
      table_counts[table] += 1
      file_prefix = "01" if table == "customers" else "02" if table == "orders" else "03"
      filename = f"{file_prefix}_{table}_part{table_counts[table]:02d}.sql"
      content = "-- Run this chunk in Supabase SQL Editor\n" + chunk_sql
      write_chunk(OUT_DIR / filename, content)

  # Helpful run order text file.
  files = sorted(p.name for p in OUT_DIR.glob("*.sql"))
  run_order = "\n".join(
    [
      "Run files in this exact order:",
      *files,
      "",
      "If a file is still too large for SQL Editor, split that file manually",
      "into smaller complete SQL statements ending in semicolons.",
    ]
  )
  write_chunk(OUT_DIR / "RUN_ORDER.txt", run_order)


if __name__ == "__main__":
  main()
