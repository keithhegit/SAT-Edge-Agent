from __future__ import annotations

import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver


_CACHE: dict[str, SqliteSaver] = {}
_CONNECTIONS: dict[str, sqlite3.Connection] = {}


def get_sqlite_checkpointer(db_path: str) -> SqliteSaver:
    if db_path not in _CACHE:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path, check_same_thread=False)
        _CONNECTIONS[db_path] = connection
        _CACHE[db_path] = SqliteSaver(connection)
    return _CACHE[db_path]


def reset_sqlite_checkpointer_cache() -> None:
    for connection in _CONNECTIONS.values():
        connection.close()
    _CONNECTIONS.clear()
    _CACHE.clear()
