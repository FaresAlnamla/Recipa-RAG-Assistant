from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Dict, Optional

from app.config import BASE_DIR

DB_PATH = Path(BASE_DIR) / "data" / "memory" / "agent_memory.sqlite3"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_memory_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
                content TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_chat_session_created ON chat_messages(session_id, created_at);"
        )


def add_message(session_id: str, role: str, content: str) -> None:
    session_id = (session_id or "").strip()
    content = (content or "").strip()
    if not session_id or not content:
        return

    role = role if role in ("user", "assistant", "system") else "user"

    with _connect() as conn:
        conn.execute(
            "INSERT INTO chat_messages(session_id, role, content) VALUES (?,?,?)",
            (session_id, role, content),
        )


def get_history(session_id: str, limit: int = 10) -> List[Dict]:
    session_id = (session_id or "").strip()
    if not session_id:
        return []

    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT role, content
            FROM chat_messages
            WHERE session_id=?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()

    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def get_last_user_question(session_id: str, offset: int = 0) -> Optional[str]:
    session_id = (session_id or "").strip()
    if not session_id:
        return None

    # offset=0 -> last user message
    # offset=1 -> previous user message before the last, etc.
    limit = offset + 1

    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT content
            FROM chat_messages
            WHERE session_id=? AND role='user'
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()

    if not rows or len(rows) <= offset:
        return None

    return rows[offset]["content"]


def clear_session(session_id: str) -> None:
    session_id = (session_id or "").strip()
    if not session_id:
        return

    with _connect() as conn:
        conn.execute("DELETE FROM chat_messages WHERE session_id=?", (session_id,))
