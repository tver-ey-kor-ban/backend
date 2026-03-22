"""Shop/Workshop models for the repair management system."""
from datetime import datetime
from enum import Enum
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from app.models.user import User


class ShopRole(str, Enum):
    """Shop role enum."""
    OWNER = "owner"
    MECHANIC = "mechanic"
    CUSTOMER = "customer"


class ShopBase(SQLModel):
    """Base shop model with common attributes."""
    name: str = Field(index=True)
    description: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: bool = True


class Shop(ShopBase, table=True):
    """Shop/Workshop database model."""
    __tablename__ = "shops"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    # Relationships
    user_shops: List["UserShop"] = Relationship(back_populates="shop")
    
    @property
    def owner(self) -> Optional["UserShop"]:
        """Get the shop owner."""
        for us in self.user_shops:
            if us.role == "owner":
                return us
        return None
    
    @property
    def mechanics(self) -> List["UserShop"]:
        """Get all mechanics in the shop."""
        return [us for us in self.user_shops if us.role == "mechanic"]
    
    @property
    def customers(self) -> List["UserShop"]:
        """Get all customers of the shop."""
        return [us for us in self.user_shops if us.role == "customer"]


class ShopCreate(ShopBase):
    """Shop creation model."""
    pass


class ShopRead(ShopBase):
    """Shop read model."""
    id: int
    created_at: datetime


class UserShop(SQLModel, table=True):
    """Many-to-many relationship between users and shops with roles."""
    __tablename__ = "user_shops"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    shop_id: int = Field(foreign_key="shops.id")
    role: str = Field(default="mechanic")  # "owner", "mechanic", or "customer"
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    # Relationships
    user: "User" = Relationship(back_populates="user_shops")
    shop: Shop = Relationship(back_populates="user_shops")


class UserShopCreate(SQLModel):
    """User shop assignment creation model."""
    user_id: int
    shop_id: int
    role: str = "mechanic"  # or "owner"


class UserShopRead(SQLModel):
    """User shop read model."""
    id: int
    user_id: int
    shop_id: int
    role: str
    is_active: bool
    created_at: datetime
