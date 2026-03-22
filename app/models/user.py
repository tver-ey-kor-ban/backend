from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from app.models.shop import UserShop
    from app.models.appointment import Appointment
    from app.models.customer_vehicle import CustomerVehicle
    from app.models.product_order import ProductOrder


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
    refresh_tokens: List["RefreshToken"] = Relationship(back_populates="user")
    # Relationship to shops (Owner/Mechanic)
    user_shops: List["UserShop"] = Relationship(back_populates="user")
    
    @property
    def owned_shops(self) -> List["UserShop"]:
        """Get shops where user is owner."""
        return [us for us in self.user_shops if us.role == "owner" and us.is_active]
    
    @property
    def mechanic_shops(self) -> List["UserShop"]:
        """Get shops where user is mechanic."""
        return [us for us in self.user_shops if us.role == "mechanic" and us.is_active]
    
    @property
    def customer_shops(self) -> List["UserShop"]:
        """Get shops where user is customer."""
        return [us for us in self.user_shops if us.role == "customer" and us.is_active]
    
    # Relationship to appointments
    appointments: List["Appointment"] = Relationship(back_populates="customer")
    
    # Relationship to customer vehicles
    vehicles: List["CustomerVehicle"] = Relationship(back_populates="customer")
    
    # Relationship to product orders
    product_orders: List["ProductOrder"] = Relationship(back_populates="customer")


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
