"""
auth.py — Authentication module with cookie-based session persistence
Uses SQLite for user + session storage, SHA-256 for password hashing,
and secure tokens for session management.
"""

import sqlite3
import hashlib
import secrets
import os
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path(__file__).parent / "users.db"

# Session tokens valid for 7 days
SESSION_EXPIRY_DAYS = 7


def _get_db():
    """Get a database connection, creating tables if needed."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    return conn


def _hash_password(password):
    """Hash a password using SHA-256 with a salt."""
    salt = "lab_report_agent_salt_2024"
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def signup(full_name, email, password):
    """
    Register a new user.
    Returns: (success: bool, message: str)
    """
    if not full_name or not email or not password:
        return False, "All fields are required."

    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    if "@" not in email or "." not in email:
        return False, "Please enter a valid email address."

    try:
        conn = _get_db()
        conn.execute(
            "INSERT INTO users (full_name, email, password_hash) VALUES (?, ?, ?)",
            (full_name.strip(), email.strip().lower(), _hash_password(password))
        )
        conn.commit()
        conn.close()
        return True, "Account created successfully! Please log in."
    except sqlite3.IntegrityError:
        return False, "An account with this email already exists."
    except Exception as e:
        return False, f"Error: {str(e)}"


def login(email, password):
    """
    Authenticate a user and create a session token.
    Returns: (success: bool, result: dict with user+token OR error string)
    """
    if not email or not password:
        return False, "Email and password are required."

    try:
        conn = _get_db()
        cursor = conn.execute(
            "SELECT id, full_name, email FROM users WHERE email = ? AND password_hash = ?",
            (email.strip().lower(), _hash_password(password))
        )
        user = cursor.fetchone()

        if not user:
            conn.close()
            return False, "Invalid email or password."

        # Generate a secure session token
        token = secrets.token_hex(32)
        expires_at = datetime.now() + timedelta(days=SESSION_EXPIRY_DAYS)

        # Clean up old sessions for this user
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user[0],))

        # Store new session
        conn.execute(
            "INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)",
            (user[0], token, expires_at.isoformat())
        )
        conn.commit()
        conn.close()

        return True, {
            "id": user[0],
            "full_name": user[1],
            "email": user[2],
            "token": token
        }

    except Exception as e:
        return False, f"Error: {str(e)}"


def validate_session(token):
    """
    Check if a session token is valid and not expired.
    Returns: user dict if valid, None if invalid/expired.
    """
    if not token:
        return None

    try:
        conn = _get_db()
        cursor = conn.execute("""
            SELECT u.id, u.full_name, u.email, s.expires_at
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token = ?
        """, (token,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        # Check expiry
        expires_at = datetime.fromisoformat(row[3])
        if datetime.now() > expires_at:
            # Token expired — clean it up
            logout(token)
            return None

        return {
            "id": row[0],
            "full_name": row[1],
            "email": row[2],
            "token": token
        }

    except Exception:
        return None


def logout(token):
    """Remove a session token from the database."""
    if not token:
        return
    try:
        conn = _get_db()
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()
    except Exception:
        pass
