"""
Единая память диалога. Хранится в SQLite, переживает перезапуск бота.
Используется и чатом, и excel-режимом, и картинками — так что любая модель
"видит" весь предыдущий контекст, независимо от того, кто отвечал до неё.
"""
import sqlite3
import config

DB_PATH = "memory.db"
MAX_MESSAGES = 30  # сколько последних сообщений подтягивать в контекст


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    return conn


def add_message(chat_id: int, role: str, content: str):
    """role: 'user' или 'assistant'. Пишет любое событие — вопрос, ответ, факт таблицы/картинки."""
    conn = _connect()
    conn.execute(
        "INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)",
        (chat_id, role, content),
    )
    conn.commit()
    conn.close()


def get_history(chat_id: int) -> list[dict]:
    """Возвращает последние MAX_MESSAGES сообщений в формате [{'role':..,'content':..}]."""
    conn = _connect()
    rows = conn.execute(
        "SELECT role, content FROM messages WHERE chat_id = ? ORDER BY id DESC LIMIT ?",
        (chat_id, MAX_MESSAGES),
    ).fetchall()
    conn.close()
    rows.reverse()
    return [{"role": r, "content": c} for r, c in rows]


def clear_history(chat_id: int):
    conn = _connect()
    conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()
