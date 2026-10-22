import sqlite3
import time
from contextlib import contextmanager

from app.core import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL, session_id TEXT, question TEXT, standalone TEXT,
    answered INTEGER, best_distance REAL
);
CREATE TABLE IF NOT EXISTS unanswered (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL, question TEXT, status TEXT DEFAULT 'open',
    answer TEXT, resolved_ts REAL
);
"""


@contextmanager
def conn():
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(config.DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init() -> None:
    with conn() as c:
        c.executescript(SCHEMA)


def log_interaction(session_id: str, question: str, standalone: str, answered: bool, best_distance: float | None) -> None:
    with conn() as c:
        c.execute(
            "INSERT INTO interactions (ts, session_id, question, standalone, answered, best_distance) VALUES (?,?,?,?,?,?)",
            (time.time(), session_id, question, standalone, int(answered), best_distance),
        )


def recent_interactions(limit: int = 1000) -> list[dict]:
    with conn() as c:
        rows = c.execute("SELECT * FROM interactions ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def add_unanswered(question: str) -> None:
    with conn() as c:
        exists = c.execute(
            "SELECT 1 FROM unanswered WHERE status='open' AND lower(question)=lower(?)", (question,)
        ).fetchone()
        if not exists:
            c.execute("INSERT INTO unanswered (ts, question) VALUES (?, ?)", (time.time(), question))


def list_unanswered(status: str = "open") -> list[dict]:
    with conn() as c:
        rows = c.execute("SELECT * FROM unanswered WHERE status=? ORDER BY id DESC", (status,)).fetchall()
    return [dict(r) for r in rows]


def get_unanswered(item_id: int) -> dict | None:
    with conn() as c:
        row = c.execute("SELECT * FROM unanswered WHERE id=?", (item_id,)).fetchone()
    return dict(row) if row else None


def resolve_unanswered(item_id: int, status: str, answer: str | None = None) -> None:
    with conn() as c:
        c.execute(
            "UPDATE unanswered SET status=?, answer=?, resolved_ts=? WHERE id=?",
            (status, answer, time.time(), item_id),
        )
