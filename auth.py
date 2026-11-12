"""Registration, login, and Streamlit session-state helpers."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Any

import streamlit as st

from database import create_user, get_user_by_id, get_user_by_username, init_db


PASSWORD_ITERATIONS = 310_000


def hash_password(password: str) -> str:
    """Hash a password using a per-password salt and PBKDF2."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    return f"{PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a stored PBKDF2 hash."""
    try:
        iterations_text, salt_hex, digest_hex = stored_hash.split("$", 2)
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations_text),
        )
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(actual, expected)


def initialize_auth_state() -> None:
    """Initialize database and authentication-related session state."""
    init_db()
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("user_id", None)
    st.session_state.setdefault("user", None)


def register_user(
    username: str,
    password: str,
    nickname: str,
    grade: str,
    major: str,
) -> tuple[bool, str]:
    """Validate and register a user."""
    username = username.strip()
    nickname = nickname.strip()
    grade = grade.strip()
    major = major.strip()

    if not all((username, password, nickname, grade, major)):
        return False, "请完整填写所有注册信息。"
    if len(password) < 6:
        return False, "密码长度至少为 6 位。"
    if get_user_by_username(username):
        return False, "该用户名已被注册。"

    create_user(username, hash_password(password), nickname, grade, major)
    return True, "注册成功，请登录。"


def login_user(username: str, password: str) -> tuple[bool, str]:
    """Validate credentials and store the authenticated user in session state."""
    user = get_user_by_username(username.strip())
    if user is None or not verify_password(password, user["password_hash"]):
        return False, "用户名或密码错误。"

    st.session_state.authenticated = True
    st.session_state.user_id = user["id"]
    st.session_state.user = user
    return True, "登录成功。"


def logout_user() -> None:
    """Clear the current authenticated session."""
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.user = None


def refresh_current_user() -> dict[str, Any] | None:
    """Reload the current user from SQLite after a profile update."""
    user_id = st.session_state.get("user_id")
    if user_id is None:
        return None
    user = get_user_by_id(int(user_id))
    st.session_state.user = user
    return user


def current_user() -> dict[str, Any] | None:
    """Return the authenticated user from session state."""
    if not st.session_state.get("authenticated"):
        return None
    return st.session_state.get("user")
