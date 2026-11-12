from __future__ import annotations

import hashlib
import hmac
import os
import sqlite3
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).resolve().parent / "zhenzhi_agent.db"


@dataclass
class User:
    id: int
    username: str
    quota: int
    student_verified: int
    free_until: Optional[str]


def get_connection(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | str = DB_PATH) -> None:
    conn = get_connection(db_path)
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL DEFAULT '',
                quota INTEGER NOT NULL DEFAULT 20,
                student_verified INTEGER NOT NULL DEFAULT 0,
                free_until TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "password_salt" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN password_salt TEXT NOT NULL DEFAULT ''")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS checkins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                checkin_date TEXT NOT NULL,
                UNIQUE(user_id, checkin_date),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS student_verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                student_id TEXT NOT NULL,
                proof_note TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                reviewed_at TEXT,
                UNIQUE(user_id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS todo_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS course_schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                course_name TEXT NOT NULL,
                slot TEXT NOT NULL,
                location TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
    conn.close()


def hash_password(password: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        200_000,
    )
    return digest.hex()


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def create_user(username: str, password: str, db_path: Path | str = DB_PATH) -> bool:
    conn = get_connection(db_path)
    try:
        salt = os.urandom(16).hex()
        with conn:
            conn.execute(
                "INSERT INTO users(username, password_hash, password_salt, created_at) VALUES(?, ?, ?, ?)",
                (username.strip(), hash_password(password, salt), salt, utc_now_iso()),
            )
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def authenticate(username: str, password: str, db_path: Path | str = DB_PATH) -> Optional[User]:
    conn = get_connection(db_path)
    row = conn.execute(
        """
        SELECT id, username, quota, student_verified, free_until, password_hash, password_salt
        FROM users
        WHERE username = ?
        """,
        (username.strip(),),
    ).fetchone()
    conn.close()
    if not row:
        return None
    candidate = hash_password(password, row["password_salt"])
    if not hmac.compare_digest(candidate, row["password_hash"]):
        return None
    return User(
        id=row["id"],
        username=row["username"],
        quota=row["quota"],
        student_verified=row["student_verified"],
        free_until=row["free_until"],
    )


def checkin(user_id: int, db_path: Path | str = DB_PATH, reward: int = 5) -> tuple[bool, str]:
    today = date.today().isoformat()
    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute(
                "INSERT INTO checkins(user_id, checkin_date) VALUES(?, ?)",
                (user_id, today),
            )
            conn.execute("UPDATE users SET quota = quota + ? WHERE id = ?", (reward, user_id))
        return True, f"签到成功，已获得 {reward} 额度。"
    except sqlite3.IntegrityError:
        return False, "今日已签到。"
    finally:
        conn.close()


def submit_student_verification(
    user_id: int,
    student_id: str,
    proof_note: str,
    db_path: Path | str = DB_PATH,
) -> None:
    conn = get_connection(db_path)
    with conn:
        conn.execute(
            """
            INSERT INTO student_verifications(user_id, student_id, proof_note, status)
            VALUES(?, ?, ?, 'pending')
            ON CONFLICT(user_id) DO UPDATE SET
                student_id = excluded.student_id,
                proof_note = excluded.proof_note,
                status = 'pending',
                reviewed_at = NULL
            """,
            (user_id, student_id.strip(), proof_note.strip()),
        )
    conn.close()


def review_student_verification(
    user_id: int,
    approved: bool,
    db_path: Path | str = DB_PATH,
    free_years: int = 4,
    bonus_quota: int = 10000,
) -> None:
    status = "approved" if approved else "rejected"
    conn = get_connection(db_path)
    with conn:
        conn.execute(
            "UPDATE student_verifications SET status = ?, reviewed_at = ? WHERE user_id = ?",
            (status, utc_now_iso(), user_id),
        )
        if approved:
            free_until = date(date.today().year + free_years, date.today().month, date.today().day).isoformat()
            conn.execute(
                "UPDATE users SET student_verified = 1, free_until = ?, quota = MAX(quota, ?) WHERE id = ?",
                (free_until, bonus_quota, user_id),
            )
    conn.close()


def add_todo(user_id: int, content: str, db_path: Path | str = DB_PATH) -> None:
    conn = get_connection(db_path)
    with conn:
        conn.execute(
            "INSERT INTO todo_items(user_id, content, created_at) VALUES(?, ?, ?)",
            (user_id, content.strip(), utc_now_iso()),
        )
    conn.close()


def list_todos(user_id: int, db_path: Path | str = DB_PATH) -> list[sqlite3.Row]:
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT id, content, done FROM todo_items WHERE user_id = ? ORDER BY id DESC", (user_id,)
    ).fetchall()
    conn.close()
    return rows


def toggle_todo(todo_id: int, done: bool, db_path: Path | str = DB_PATH) -> None:
    conn = get_connection(db_path)
    with conn:
        conn.execute("UPDATE todo_items SET done = ? WHERE id = ?", (1 if done else 0, todo_id))
    conn.close()


def add_course(user_id: int, course_name: str, slot: str, location: str, db_path: Path | str = DB_PATH) -> None:
    conn = get_connection(db_path)
    with conn:
        conn.execute(
            "INSERT INTO course_schedule(user_id, course_name, slot, location, created_at) VALUES(?, ?, ?, ?, ?)",
            (user_id, course_name.strip(), slot.strip(), location.strip(), utc_now_iso()),
        )
    conn.close()


def list_courses(user_id: int, db_path: Path | str = DB_PATH) -> list[sqlite3.Row]:
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT course_name, slot, location FROM course_schedule WHERE user_id = ? ORDER BY id DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return rows


def consume_quota(user_id: int, amount: int = 1, db_path: Path | str = DB_PATH) -> bool:
    conn = get_connection(db_path)
    with conn:
        current = conn.execute("SELECT quota FROM users WHERE id = ?", (user_id,)).fetchone()
        if not current or current["quota"] < amount:
            return False
        conn.execute("UPDATE users SET quota = quota - ? WHERE id = ?", (amount, user_id))
    conn.close()
    return True


def get_user_by_id(user_id: int, db_path: Path | str = DB_PATH) -> Optional[User]:
    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT id, username, quota, student_verified, free_until FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return User(**dict(row))
