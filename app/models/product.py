"""Product and Service models for shop management."""
from datetime import datetime
from enum import Enum
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from app.models.vehicle import ProductVehicle
    from app.models.category import ProductCategory


class ProductBase(SQLModel):
    """Base product model."""
    name: str = Field(index=True)
    description: Optional[str] = None
    price: float = Field(default=0.0)
    cost: Optional[float] = None
    stock_quantity: int = Field(default=0)
    sku: Optional[str] = None
    is_active: bool = True
    category_id: Optional[int] = Field(default=None, foreign_key="product_categories.id")
    
    # Image fields for visual search
    image_url: Optional[str] = None  # Main product image
    image_embedding: Optional[str] = None  # Vector embedding for image search (base64 encoded)
    thumbnail_url: Optional[str] = None  # Small thumbnail


class Product(ProductBase, table=True):
    """Product database model."""
    __tablename__ = "products"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    shop_id: int = Field(foreign_key="shops.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    # Vehicle compatibility
    vehicle_compatibilities: List["ProductVehicle"] = Relationship(back_populates="product")
    
    # Category
    category: Optional["ProductCategory"] = Relationship(back_populates="products")


class ProductCreate(ProductBase):
    """Product creation model."""
    pass


class ProductRead(ProductBase):
    """Product read model."""
    id: int
    shop_id: int
    created_at: datetime


class ServiceType(str, Enum):
    """Service type enum."""
    SHOP_BASED = "shop_based"      # Customer brings vehicle to shop
    MOBILE = "mobile"              # Mechanic goes to customer location
    PICKUP_DROP = "pickup_drop"    # Shop picks up vehicle, services, returns


class ServiceBase(SQLModel):
    """Base service model."""
    name: str = Field(index=True)
    description: Optional[str] = None
    price: float = Field(default=0.0)
    duration_minutes: Optional[int] = None
    is_active: bool = True
    
    # Service type
    service_type: ServiceType = Field(default=ServiceType.SHOP_BASED)
    
    # Mobile service fields
    mobile_service_area: Optional[str] = None  # Area coverage for mobile service
    mobile_service_fee: Optional[float] = None  # Additional fee for mobile service
    
    # Image fields
    image_url: Optional[str] = None  # Main service image
    thumbnail_url: Optional[str] = None  # Small thumbnail


class Service(ServiceBase, table=True):
    """Service database model."""
    __tablename__ = "services"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    shop_id: int = Field(foreign_key="shops.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class ServiceCreate(ServiceBase):
    """Service creation model."""
    pass


class ServiceRead(ServiceBase):
    """Service read model."""
    id: int
    shop_id: int
    created_at: datetime
