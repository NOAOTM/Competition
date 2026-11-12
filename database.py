"""SQLite persistence helpers for 真知 Agent."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "zhenzhi_agent.db"


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with row access by column name."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db() -> None:
    """Create the user table if it does not exist yet."""
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                nickname TEXT NOT NULL,
                grade TEXT NOT NULL,
                major TEXT NOT NULL,
                balance INTEGER NOT NULL DEFAULT 0 CHECK (balance >= 0),
                verification_status TEXT NOT NULL DEFAULT '未认证'
                    CHECK (verification_status IN ('未认证', '审核中', '已认证', '未通过')),
                verification_image_path TEXT,
                expires_at TEXT,
                last_check_in_date TEXT,
                created_at TEXT NOT NULL
            )
            """
        )


def create_user(
    username: str,
    password_hash: str,
    nickname: str,
    grade: str,
    major: str,
) -> int:
    """Create a user and return its database id."""
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO users (
                username, password_hash, nickname, grade, major, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                username,
                password_hash,
                nickname,
                grade,
                major,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        return int(cursor.lastrowid)


def get_user_by_username(username: str) -> dict[str, Any] | None:
    """Fetch a user by username."""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    """Fetch a user by id."""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def check_in_user(user_id: int) -> tuple[bool, int]:
    """Add 10 credits when the user has not checked in today."""
    today = date.today().isoformat()
    with get_connection() as connection:
        row = connection.execute(
            "SELECT last_check_in_date, balance FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            return False, 0
        if row["last_check_in_date"] == today:
            return False, int(row["balance"])

        connection.execute(
            """
            UPDATE users
            SET balance = balance + 10, last_check_in_date = ?
            WHERE id = ?
            """,
            (today, user_id),
        )
        return True, int(row["balance"]) + 10


def submit_verification(user_id: int, image_path: str) -> bool:
    """Mark a user's student verification as pending."""
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE users
            SET verification_status = '审核中',
                verification_image_path = ?
            WHERE id = ?
            """,
            (image_path, user_id),
        )
        return cursor.rowcount > 0
