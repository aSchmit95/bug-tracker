import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.getenv("DB_PATH", "bugs.db")


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bugs (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                title               TEXT    NOT NULL,
                description         TEXT    DEFAULT '',
                steps_to_reproduce  TEXT    DEFAULT '',
                expected_result     TEXT    DEFAULT '',
                actual_result       TEXT    DEFAULT '',
                severity            TEXT    NOT NULL DEFAULT 'medium',
                status              TEXT    NOT NULL DEFAULT 'open',
                reporter            TEXT    DEFAULT '',
                created_at          TEXT    DEFAULT (datetime('now')),
                updated_at          TEXT    DEFAULT (datetime('now'))
            )
        """)


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def create_bug(title: str, description: str = "", steps_to_reproduce: str = "",
               expected_result: str = "", actual_result: str = "",
               severity: str = "medium", reporter: str = "") -> dict:
    with get_conn() as conn:
        cursor = conn.execute(
            """INSERT INTO bugs
               (title, description, steps_to_reproduce, expected_result,
                actual_result, severity, reporter)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (title, description, steps_to_reproduce, expected_result,
             actual_result, severity, reporter),
        )
        row = conn.execute(
            "SELECT * FROM bugs WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return dict(row)


def get_bugs(status: str | None = None, severity: str | None = None) -> list[dict]:
    query = "SELECT * FROM bugs WHERE 1=1"
    params: list = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if severity:
        query += " AND severity = ?"
        params.append(severity)
    query += " ORDER BY id DESC"
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def get_bug(bug_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM bugs WHERE id = ?", (bug_id,)
        ).fetchone()
        return dict(row) if row else None


def update_bug(bug_id: int, fields: dict) -> dict | None:
    if not fields:
        return get_bug(bug_id)
    fields["updated_at"] = "datetime('now')"
    set_clause = ", ".join(
        f"{k} = datetime('now')" if v == "datetime('now')" else f"{k} = ?"
        for k, v in fields.items()
    )
    values = [v for v in fields.values() if v != "datetime('now')"]
    with get_conn() as conn:
        conn.execute(
            f"UPDATE bugs SET {set_clause} WHERE id = ?",
            [*values, bug_id],
        )
        row = conn.execute(
            "SELECT * FROM bugs WHERE id = ?", (bug_id,)
        ).fetchone()
        return dict(row) if row else None


def delete_bug(bug_id: int) -> bool:
    with get_conn() as conn:
        cursor = conn.execute("DELETE FROM bugs WHERE id = ?", (bug_id,))
        return cursor.rowcount > 0


def get_stats() -> dict:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) as count FROM bugs GROUP BY status"
        ).fetchall()
        stats = {"open": 0, "in_progress": 0, "closed": 0}
        for row in rows:
            stats[row["status"]] = row["count"]
        return stats
