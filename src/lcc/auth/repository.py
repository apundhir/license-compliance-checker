"""User repository for managing users and API keys."""

from __future__ import annotations

import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from lcc.auth.core import User, UserRole, get_password_hash


class UserRepository:
    """Repository for managing users and API keys."""

    def __init__(self, db_path: Path):
        """
        Initialize user repository.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    email TEXT UNIQUE,
                    full_name TEXT,
                    hashed_password TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    disabled INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    key_id TEXT PRIMARY KEY,
                    key_hash TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    username TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    disabled INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    last_used_at TEXT,
                    expires_at TEXT,
                    FOREIGN KEY (username) REFERENCES users(username)
                )
            """)

            # Create default admin user if no users exist
            cursor = conn.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                now = datetime.now(timezone.utc).isoformat()
                conn.execute("""
                    INSERT INTO users (username, email, full_name, hashed_password, role, disabled, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    "admin",
                    "admin@example.com",
                    "Administrator",
                    get_password_hash("admin"),  # Default password, should be changed
                    UserRole.ADMIN.value,
                    0,
                    now,
                    now
                ))

            conn.commit()
        finally:
            conn.close()

    def get_user(self, username: str) -> Optional[User]:
        """
        Get user by username.

        Args:
            username: Username to look up

        Returns:
            User if found, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,)
            )
            row = cursor.fetchone()

            if row is None:
                return None

            return User(
                username=row["username"],
                email=row["email"],
                full_name=row["full_name"],
                hashed_password=row["hashed_password"],
                role=UserRole(row["role"]),
                disabled=bool(row["disabled"])
            )
        finally:
            conn.close()

    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.

        Args:
            email: Email to look up

        Returns:
            User if found, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                "SELECT * FROM users WHERE email = ?",
                (email,)
            )
            row = cursor.fetchone()

            if row is None:
                return None

            return User(
                username=row["username"],
                email=row["email"],
                full_name=row["full_name"],
                hashed_password=row["hashed_password"],
                role=UserRole(row["role"]),
                disabled=bool(row["disabled"])
            )
        finally:
            conn.close()

    def create_user(
        self,
        username: str,
        password: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        role: UserRole = UserRole.USER
    ) -> User:
        """
        Create a new user.

        Args:
            username: Username
            password: Plain text password (will be hashed)
            email: Optional email
            full_name: Optional full name
            role: User role

        Returns:
            Created user

        Raises:
            ValueError: If user already exists
        """
        conn = sqlite3.connect(self.db_path)
        try:
            now = datetime.now(timezone.utc).isoformat()
            hashed_password = get_password_hash(password)

            conn.execute("""
                INSERT INTO users (username, email, full_name, hashed_password, role, disabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                username,
                email,
                full_name,
                hashed_password,
                role.value,
                0,
                now,
                now
            ))

            conn.commit()

            return User(
                username=username,
                email=email,
                full_name=full_name,
                hashed_password=hashed_password,
                role=role,
                disabled=False
            )

        except sqlite3.IntegrityError:
            raise ValueError(f"User '{username}' already exists")
        finally:
            conn.close()

    def update_password(self, username: str, new_password: str) -> None:
        """
        Update user password.

        Args:
            username: Username
            new_password: New plain text password (will be hashed)
        """
        conn = sqlite3.connect(self.db_path)
        try:
            hashed_password = get_password_hash(new_password)
            now = datetime.now(timezone.utc).isoformat()

            conn.execute("""
                UPDATE users
                SET hashed_password = ?, updated_at = ?
                WHERE username = ?
            """, (hashed_password, now, username))

            conn.commit()
        finally:
            conn.close()

    def disable_user(self, username: str) -> None:
        """
        Disable a user.

        Args:
            username: Username to disable
        """
        conn = sqlite3.connect(self.db_path)
        try:
            now = datetime.now(timezone.utc).isoformat()
            conn.execute("""
                UPDATE users
                SET disabled = 1, updated_at = ?
                WHERE username = ?
            """, (now, username))
            conn.commit()
        finally:
            conn.close()

    def create_api_key(
        self,
        username: str,
        name: str,
        role: Optional[UserRole] = None,
        expires_at: Optional[datetime] = None
    ) -> tuple[str, str]:
        """
        Create an API key for a user.

        Args:
            username: Username who owns the key
            name: Descriptive name for the key
            role: Optional role for the key (defaults to user's role)
            expires_at: Optional expiration datetime

        Returns:
            Tuple of (key_id, raw_key) - raw_key must be saved by caller

        Raises:
            ValueError: If user does not exist
        """
        # Verify user exists
        user = self.get_user(username)
        if user is None:
            raise ValueError(f"User '{username}' does not exist")

        # Generate API key
        key_id = f"lcc_{secrets.token_urlsafe(16)}"
        raw_key = secrets.token_urlsafe(32)
        key_hash = get_password_hash(raw_key)

        conn = sqlite3.connect(self.db_path)
        try:
            now = datetime.now(timezone.utc).isoformat()
            expires_str = expires_at.isoformat() if expires_at else None

            conn.execute("""
                INSERT INTO api_keys (key_id, key_hash, name, username, role, disabled, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                key_id,
                key_hash,
                name,
                username,
                (role or user.role).value,
                0,
                now,
                expires_str
            ))

            conn.commit()

            # Return both key_id and raw key (key is shown only once)
            return (key_id, f"{key_id}.{raw_key}")

        finally:
            conn.close()

    def verify_api_key(self, api_key: str) -> Optional[User]:
        """
        Verify an API key and return the associated user.

        Args:
            api_key: API key in format "key_id.raw_key"

        Returns:
            User if key is valid, None otherwise
        """
        if "." not in api_key:
            return None

        key_id, raw_key = api_key.split(".", 1)

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute("""
                SELECT * FROM api_keys
                WHERE key_id = ? AND disabled = 0
            """, (key_id,))

            row = cursor.fetchone()
            if row is None:
                return None

            # Check if key is expired
            if row["expires_at"]:
                expires_at = datetime.fromisoformat(row["expires_at"])
                if datetime.now(timezone.utc) > expires_at:
                    return None

            # Verify key hash
            from lcc.auth.core import verify_password
            if not verify_password(raw_key, row["key_hash"]):
                return None

            # Update last used timestamp
            now = datetime.now(timezone.utc).isoformat()
            conn.execute("""
                UPDATE api_keys
                SET last_used_at = ?
                WHERE key_id = ?
            """, (now, key_id))
            conn.commit()

            # Return user associated with key
            return User(
                username=row["username"],
                role=UserRole(row["role"]),
                disabled=False
            )

        finally:
            conn.close()

    def revoke_api_key(self, key_id: str) -> None:
        """
        Revoke (disable) an API key.

        Args:
            key_id: API key ID to revoke
        """
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                UPDATE api_keys
                SET disabled = 1
                WHERE key_id = ?
            """, (key_id,))
            conn.commit()
        finally:
            conn.close()
