# Copyright 2025 Ajay Pundhir
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Core authentication and authorization logic."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

# Configuration
SECRET_KEY = os.getenv("LCC_SECRET_KEY", "")
ALGORITHM = "HS256"


def _get_secret_key() -> str:
    """Return the secret key, raising an error if it is not configured.

    The check is deferred so that importing this module does not fail
    in environments that do not need authentication (CLI, tests, etc.).
    """
    key = SECRET_KEY or os.getenv("LCC_SECRET_KEY", "")
    if not key:
        raise RuntimeError(
            "LCC_SECRET_KEY environment variable is required. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    return key
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


# Password hashing
# Use argon2 instead of bcrypt to avoid password length limitations
# argon2 is more modern and recommended for new applications
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated=["bcrypt"],
    argon2__memory_cost=65536,
    argon2__time_cost=3,
    argon2__parallelism=4,
)

# HTTP Bearer token scheme
security = HTTPBearer()


class UserRole(StrEnum):
    """User roles for RBAC."""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"
    API_KEY = "api_key"


class User(BaseModel):
    """User model."""
    username: str
    email: EmailStr | None = None
    full_name: str | None = None
    disabled: bool = False
    role: UserRole = UserRole.USER
    hashed_password: str | None = None
    must_change_password: bool = False  # Force password change on first login


class Token(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60
    must_change_password: bool = False


class TokenData(BaseModel):
    """Token payload data."""
    username: str | None = None
    role: UserRole | None = None
    exp: datetime | None = None


# Password utilities
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using argon2."""
    return pwd_context.hash(password)


# JWT utilities
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Dictionary containing user claims (sub, role, etc.)
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, _get_secret_key(), algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    Create a JWT refresh token with longer expiration.

    Args:
        data: Dictionary containing user claims

    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, _get_secret_key(), algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> TokenData:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string

    Returns:
        TokenData with decoded claims

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, _get_secret_key(), algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        exp: int = payload.get("exp")

        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Convert exp timestamp to datetime
        exp_datetime = datetime.fromtimestamp(exp, tz=UTC) if exp else None

        return TokenData(
            username=username,
            role=UserRole(role) if role else None,
            exp=exp_datetime
        )

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user_repository=None  # Will be injected via dependency
) -> User:
    """
    Get current user from JWT token.

    Args:
        credentials: HTTP authorization credentials from request
        user_repository: User repository for fetching user data

    Returns:
        Current authenticated user

    Raises:
        HTTPException: If credentials are invalid
    """
    token = credentials.credentials
    token_data = decode_token(token)

    # In a real implementation, fetch user from database
    # For now, return user from token data
    if user_repository:
        user = user_repository.get_user(token_data.username)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    # Default: create user from token data
    return User(
        username=token_data.username,
        role=token_data.role or UserRole.USER,
        disabled=False
    )


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get current active user (ensures user is not disabled).

    Args:
        current_user: Current user from get_current_user

    Returns:
        Current active user

    Raises:
        HTTPException: If user is disabled
    """
    if current_user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def require_role(required_role: UserRole):
    """
    Dependency that requires a specific role.

    Usage:
        @app.get("/admin/endpoint")
        def admin_endpoint(user: User = Depends(require_role(UserRole.ADMIN))):
            ...

    Args:
        required_role: The required user role

    Returns:
        Dependency function that checks role
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        # Admin role has access to everything
        if current_user.role == UserRole.ADMIN:
            return current_user

        # Check specific role
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role.value}"
            )

        return current_user

    return role_checker


def authenticate_user(username: str, password: str, user_repository=None) -> User | None:
    """
    Authenticate a user by username and password.

    Args:
        username: Username
        password: Plain text password
        user_repository: User repository for fetching user data

    Returns:
        User if authentication succeeds, None otherwise
    """
    if user_repository:
        user = user_repository.get_user(username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    # Default: no user repository, authentication fails
    return None
