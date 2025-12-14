import argparse
import os

import pandas as pd
import clickhouse_connect

DEFAULT_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
DEFAULT_PORT = int(os.getenv("CLICKHOUSE_PORT", "8123"))
DEFAULT_DB = os.getenv("CLICKHOUSE_DB", "roas")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="Path to cohort CSV (test_task_cl.csv)")
    ap.add_argument("--table", default="cohort_metrics", help="Target table name")
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--db", default=DEFAULT_DB)
    args = ap.parse_args()

    df = pd.read_csv(args.csv)

    client = clickhouse_connect.get_client(host=args.host, port=args.port, database=args.db)

    # Create schema if needed
    schema_path = os.path.join(os.path.dirname(__file__), "..", "sql", "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        for stmt in f.read().split(";"):
            stmt = stmt.strip()
            if stmt:
                client.command(stmt)

    # Insert into roas.cohort_metrics
    full_table = f"{args.db}.{args.table}"
    client.insert_df(full_table, df)
    print(f"Inserted {len(df)} rows into {full_table}")


if __name__ == "__main__":
    main()
