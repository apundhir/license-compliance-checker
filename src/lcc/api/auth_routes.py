"""Authentication routes for the API."""

from __future__ import annotations

from datetime import timedelta
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr

from lcc.auth.core import (
    User,
    UserRole,
    Token,
    create_access_token,
    create_refresh_token,
    get_current_active_user,
    require_role,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from lcc.auth.repository import UserRepository


class LoginRequest(BaseModel):
    """Login request model."""
    username: str
    password: str


class RegisterRequest(BaseModel):
    """User registration request."""
    username: str
    password: str
    email: EmailStr
    full_name: str | None = None


class CreateAPIKeyRequest(BaseModel):
    """Create API key request."""
    name: str
    role: UserRole = UserRole.USER
    expires_days: int | None = None


class APIKeyResponse(BaseModel):
    """API key response (shown only once)."""
    key_id: str
    api_key: str
    warning: str = "Save this key securely. It will not be shown again."


class ChangePasswordRequest(BaseModel):
    """Change password request."""
    current_password: str
    new_password: str


def create_auth_router(user_repo: UserRepository) -> APIRouter:
    """
    Create authentication router.

    Args:
        user_repo: User repository instance

    Returns:
        Configured auth router
    """
    router = APIRouter(prefix="/auth", tags=["Authentication"])

    # Create a custom dependency that uses the user_repo
    async def get_current_user_with_db(
        credentials = Depends(get_current_active_user)
    ) -> User:
        """Get current user from database using the provided user_repo."""
        from lcc.auth.core import security, decode_token
        from fastapi.security import HTTPAuthorizationCredentials

        # Get credentials
        if isinstance(credentials, User):
            # Already got the user, just fetch full details from DB
            db_user = user_repo.get_user(credentials.username)
            if db_user and not db_user.disabled:
                return db_user
            elif db_user and db_user.disabled:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Inactive user"
                )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

    @router.post("/login", response_model=Token)
    async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
        """
        Login with username and password to get access token.

        Args:
            form_data: OAuth2 password request form

        Returns:
            Access and refresh tokens

        Raises:
            HTTPException: If credentials are invalid
        """
        from lcc.auth.core import authenticate_user

        user = authenticate_user(form_data.username, form_data.password, user_repo)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if user.disabled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled"
            )

        # Create tokens
        access_token = create_access_token(
            data={"sub": user.username, "role": user.role.value}
        )
        refresh_token = create_refresh_token(
            data={"sub": user.username, "role": user.role.value}
        )

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    @router.post("/register", response_model=Dict[str, str], status_code=201)
    async def register(
        request: RegisterRequest,
        current_user: User = Depends(require_role(UserRole.ADMIN))
    ) -> Dict[str, str]:
        """
        Register a new user (admin only).

        Args:
            request: Registration request
            current_user: Current admin user

        Returns:
            Success message

        Raises:
            HTTPException: If user already exists
        """
        try:
            user_repo.create_user(
                username=request.username,
                password=request.password,
                email=request.email,
                full_name=request.full_name,
                role=UserRole.USER
            )
            return {"message": f"User '{request.username}' created successfully"}

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    @router.get("/me", response_model=User)
    async def get_current_user_info(
        current_user: User = Depends(get_current_user_with_db)
    ) -> User:
        """
        Get current user information.

        Args:
            current_user: Current authenticated user

        Returns:
            User information (without password hash)
        """
        # Don't return password hash
        return User(
            username=current_user.username,
            email=current_user.email,
            full_name=current_user.full_name,
            role=current_user.role,
            disabled=current_user.disabled
        )

    @router.post("/change-password", response_model=Dict[str, str])
    async def change_password(
        request: ChangePasswordRequest,
        current_user: User = Depends(get_current_active_user)
    ) -> Dict[str, str]:
        """
        Change current user's password.

        Args:
            request: Change password request
            current_user: Current authenticated user

        Returns:
            Success message

        Raises:
            HTTPException: If current password is incorrect
        """
        from lcc.auth.core import verify_password

        # Verify current password
        user = user_repo.get_user(current_user.username)
        if not user or not verify_password(request.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )

        # Update password
        user_repo.update_password(current_user.username, request.new_password)

        return {"message": "Password changed successfully"}

    @router.post("/api-keys", response_model=APIKeyResponse, status_code=201)
    async def create_api_key(
        request: CreateAPIKeyRequest,
        current_user: User = Depends(get_current_active_user)
    ) -> APIKeyResponse:
        """
        Create an API key for current user.

        Args:
            request: API key creation request
            current_user: Current authenticated user

        Returns:
            API key (shown only once)
        """
        from datetime import datetime, timezone, timedelta

        expires_at = None
        if request.expires_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=request.expires_days)

        # Only admins can create keys with admin role
        if request.role == UserRole.ADMIN and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can create admin API keys"
            )

        key_id, api_key = user_repo.create_api_key(
            username=current_user.username,
            name=request.name,
            role=request.role,
            expires_at=expires_at
        )

        return APIKeyResponse(
            key_id=key_id,
            api_key=api_key
        )

    @router.delete("/api-keys/{key_id}", response_model=Dict[str, str])
    async def revoke_api_key(
        key_id: str,
        current_user: User = Depends(get_current_active_user)
    ) -> Dict[str, str]:
        """
        Revoke (delete) an API key.

        Args:
            key_id: API key ID to revoke
            current_user: Current authenticated user

        Returns:
            Success message
        """
        user_repo.revoke_api_key(key_id)
        return {"message": f"API key '{key_id}' revoked successfully"}

    @router.post("/refresh", response_model=Token)
    async def refresh_token(
        refresh_token: str,
    ) -> Token:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Refresh token string

        Returns:
            New access and refresh tokens
        """
        from lcc.auth.core import decode_token

        try:
            token_data = decode_token(refresh_token)

            # Create new tokens
            access_token = create_access_token(
                data={"sub": token_data.username, "role": token_data.role.value}
            )
            new_refresh_token = create_refresh_token(
                data={"sub": token_data.username, "role": token_data.role.value}
            )

            return Token(
                access_token=access_token,
                refresh_token=new_refresh_token,
                expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
            )

        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

    return router
