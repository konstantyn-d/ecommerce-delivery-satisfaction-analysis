"""Run the numbered SQL files in sql/ against the project DuckDB database.

Usage (from the repository root):
    python run_sql.py                  # run every file in sql/ in numbered order
    python run_sql.py 00_load_raw.sql  # run only the named file(s)

The database file (data/processed/olist.duckdb) is a build artefact: it is not committed
and can always be rebuilt from the raw CSV files by running this script.
"""

import os
import sys
import time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent
SQL_DIR = ROOT / "sql"
DB_PATH = ROOT / "data" / "processed" / "olist.duckdb"


def main() -> None:
    # The SQL files use paths relative to the repository root (e.g. 'data/raw/...').
    os.chdir(ROOT)

    requested = sys.argv[1:]
    files = [SQL_DIR / name for name in requested] if requested else sorted(SQL_DIR.glob("*.sql"))

    con = duckdb.connect(str(DB_PATH))
    for path in files:
        start = time.time()
        con.execute(path.read_text(encoding="utf-8"))
        print(f"ok  {path.name}  ({time.time() - start:.1f}s)")

    print("\nTables in the database:")
    rows = con.execute(
        "SELECT schema_name, table_name, estimated_size "
        "FROM duckdb_tables() ORDER BY schema_name, table_name"
    ).fetchall()
    for schema, table, size in rows:
        print(f"  {schema}.{table:<22} {size:>10,} rows")
    con.close()


if __name__ == "__main__":
    main()
