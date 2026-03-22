"""Local authentication service."""
from datetime import datetime
from typing import Optional
from sqlmodel import Session, select

from app.models.user import User, UserCreate, RefreshToken
from app.core.security import (
    get_password_hash, verify_password, create_access_token, create_refresh_token,
    decode_refresh_token
)


class AuthService:
    """Service for local authentication operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        statement = select(User).where(User.username == username)
        return self.session.exec(statement).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        statement = select(User).where(User.email == email)
        return self.session.exec(statement).first()
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self.session.get(User, user_id)
    
    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        # Check if user already exists
        if self.get_user_by_email(user_data.email):
            raise ValueError("Email already registered")
        if self.get_user_by_username(user_data.username):
            raise ValueError("Username already taken")
        
        # Create user
        hashed_password = get_password_hash(user_data.password)
        user = User(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            hashed_password=hashed_password,
            roles=user_data.roles,
            is_active=user_data.is_active,
            is_superuser=user_data.is_superuser
        )
        
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password."""
        user = self.get_user_by_username(username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
    
    def create_refresh_token_for_user(self, user_id: int) -> str:
        """Create and store a refresh token for a user."""
        from datetime import timedelta
        from app.core.security import REFRESH_TOKEN_EXPIRE_DAYS
        
        # Create JWT refresh token
        refresh_token_jwt = create_refresh_token(user_id)
        
        # Store in database
        expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token = RefreshToken(
            token=refresh_token_jwt,
            user_id=user_id,
            expires_at=expires_at
        )
        self.session.add(refresh_token)
        self.session.commit()
        
        return refresh_token_jwt
    
    def get_refresh_token(self, token: str) -> Optional[RefreshToken]:
        """Get refresh token from database."""
        statement = select(RefreshToken).where(RefreshToken.token == token)
        return self.session.exec(statement).first()
    
    def revoke_refresh_token(self, token: str) -> bool:
        """Revoke a refresh token."""
        refresh_token = self.get_refresh_token(token)
        if not refresh_token:
            return False
        refresh_token.revoked = True
        self.session.commit()
        return True
    
    def revoke_all_user_refresh_tokens(self, user_id: int) -> int:
        """Revoke all refresh tokens for a user. Returns count of revoked tokens."""
        from sqlmodel import col
        statement = select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            col(RefreshToken.revoked).is_(False)
        )
        tokens = self.session.exec(statement).all()
        count = 0
        for token in tokens:
            token.revoked = True
            count += 1
        self.session.commit()
        return count
    
    def refresh_access_token(self, refresh_token: str) -> Optional[dict]:
        """Refresh access token using refresh token."""
        # Verify JWT refresh token
        user_id = decode_refresh_token(refresh_token)
        if not user_id:
            return None
        
        # Get token from database
        db_token = self.get_refresh_token(refresh_token)
        if not db_token:
            return None
        
        # Check if token is revoked or expired
        if db_token.revoked:
            return None
        if db_token.expires_at < datetime.utcnow():
            return None
        
        # Get user
        user = self.get_user_by_id(user_id)
        if not user or not user.is_active:
            return None
        
        # Convert roles string to list
        roles_list = user.roles.split(",") if user.roles else ["user"]
        
        # Create new access token
        access_token = create_access_token(
            user_id=user.id,
            username=user.username,
            email=user.email,
            roles=roles_list,
            is_superuser=user.is_superuser
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
    
    def login(self, username: str, password: str) -> Optional[dict]:
        """Login user and return access token and refresh token."""
        user = self.authenticate_user(username, password)
        if not user:
            return None
        
        # Convert roles string to list
        roles_list = user.roles.split(",") if user.roles else ["user"]
        
        # Create access token
        access_token = create_access_token(
            user_id=user.id,
            username=user.username,
            email=user.email,
            roles=roles_list,
            is_superuser=user.is_superuser
        )
        
        # Create refresh token
        refresh_token = self.create_refresh_token_for_user(user.id)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
