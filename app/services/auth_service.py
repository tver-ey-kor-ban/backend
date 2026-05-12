"""Local authentication service."""
from datetime import datetime, timedelta
from typing import Optional

from app.models.user import User, UserCreate, RefreshToken
from app.repositories.user_repository import UserRepository
from app.core.security import (
    get_password_hash, verify_password, create_access_token, create_refresh_token,
    decode_refresh_token, REFRESH_TOKEN_EXPIRE_DAYS,
)


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def get_user_by_username(self, username: str) -> Optional[User]:
        return self.user_repo.get_by_username(username)

    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.user_repo.get_by_email(email)

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        return self.user_repo.get_by_id(user_id)

    def create_user(self, user_data: UserCreate) -> User:
        if self.user_repo.get_by_email(user_data.email):
            raise ValueError("Email already registered")
        if self.user_repo.get_by_username(user_data.username):
            raise ValueError("Username already taken")

        user = User(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            hashed_password=get_password_hash(user_data.password),
            roles=user_data.roles,
            is_active=user_data.is_active,
            is_superuser=user_data.is_superuser,
        )
        return self.user_repo.save(user)

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        user = self.user_repo.get_by_username(username)
        if not user or not verify_password(password, user.hashed_password):
            return None
        return user

    def create_refresh_token_for_user(self, user_id: int) -> str:
        refresh_token_jwt = create_refresh_token(user_id)
        expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        self.user_repo.save_refresh_token(
            RefreshToken(
                token=refresh_token_jwt,
                user_id=user_id,
                expires_at=expires_at,
            )
        )
        return refresh_token_jwt

    def get_refresh_token(self, token: str) -> Optional[RefreshToken]:
        return self.user_repo.get_refresh_token(token)

    def revoke_refresh_token(self, token: str) -> bool:
        db_token = self.user_repo.get_refresh_token(token)
        if not db_token:
            return False
        self.user_repo.revoke_token(db_token)
        return True

    def revoke_all_user_refresh_tokens(self, user_id: int) -> int:
        tokens = self.user_repo.get_active_refresh_tokens(user_id)
        return self.user_repo.revoke_tokens(tokens)

    def refresh_access_token(self, refresh_token: str) -> Optional[dict]:
        user_id = decode_refresh_token(refresh_token)
        if not user_id:
            return None

        db_token = self.user_repo.get_refresh_token(refresh_token)
        if not db_token or db_token.revoked:
            return None
        if db_token.expires_at < datetime.utcnow():
            return None

        user = self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            return None

        roles_list = user.roles.split(",") if user.roles else ["user"]
        access_token = create_access_token(
            user_id=user.id,
            username=user.username,
            email=user.email,
            roles=roles_list,
            is_superuser=user.is_superuser,
        )
        return {"access_token": access_token, "token_type": "bearer"}

    def login(self, username: str, password: str) -> Optional[dict]:
        user = self.authenticate_user(username, password)
        if not user:
            return None

        roles_list = user.roles.split(",") if user.roles else ["user"]
        access_token = create_access_token(
            user_id=user.id,
            username=user.username,
            email=user.email,
            roles=roles_list,
            is_superuser=user.is_superuser,
        )
        refresh_token = self.create_refresh_token_for_user(user.id)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }
