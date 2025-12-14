from __future__ import annotations

import clickhouse_connect

from .config import CLICKHOUSE_HOST, CLICKHOUSE_PORT, CLICKHOUSE_DB


def get_client():
    return clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_PORT,
        database=CLICKHOUSE_DB,
    )
