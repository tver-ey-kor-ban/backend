from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship


class UserBase(SQLModel):
    """Base user model with common attributes."""
    email: str = Field(unique=True, index=True)
    username: str = Field(unique=True, index=True)
    full_name: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    roles: str = Field(default="user")  # Comma-separated roles for SQLite compatibility


class User(UserBase, table=True):
    """User database model."""
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    # Relationship to refresh tokens
    refresh_tokens: list["RefreshToken"] = Relationship(back_populates="user")


class UserCreate(UserBase):
    """User creation model."""
    password: str


class UserRead(UserBase):
    """User read model (excludes sensitive data)."""
    id: int
    created_at: datetime


class RefreshToken(SQLModel, table=True):
    """Refresh token model for storing refresh tokens."""
    __tablename__ = "refresh_tokens"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(unique=True, index=True)
    user_id: int = Field(foreign_key="users.id")
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    revoked: bool = Field(default=False)
    
    # Relationship to user
    user: User = Relationship(back_populates="refresh_tokens")


class RefreshTokenCreate(SQLModel):
    """Refresh token creation model."""
    token: str
    user_id: int
    expires_at: datetime


class RefreshTokenRead(SQLModel):
    """Refresh token read model."""
    id: int
    token: str
    user_id: int
    expires_at: datetime
    created_at: datetime
    revoked: bool
