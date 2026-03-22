"""Product Order models for customer self-service purchases."""
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from enum import Enum
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from app.models.user import User


class OrderStatus(str, Enum):
    """Order status enum."""
    PENDING = "pending"           # Order created, awaiting confirmation
    CONFIRMED = "confirmed"       # Shop confirmed order
    PROCESSING = "processing"     # Preparing items
    READY = "ready"               # Ready for pickup
    COMPLETED = "completed"       # Customer picked up
    CANCELLED = "cancelled"       # Cancelled


class ProductOrderBase(SQLModel):
    """Base product order model."""
    shop_id: int = Field(foreign_key="shops.id")
    customer_id: int = Field(foreign_key="users.id")
    customer_vehicle_id: Optional[int] = Field(default=None, foreign_key="customer_vehicles.id")
    
    # Order info
    status: OrderStatus = OrderStatus.PENDING
    total_amount: float = Field(default=0.0)
    
    # Pickup/Delivery info
    pickup_date: Optional[datetime] = None
    notes: Optional[str] = None  # Customer notes
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class ProductOrder(ProductOrderBase, table=True):
    """Product order database model."""
    __tablename__ = "product_orders"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Relationships
    customer: "User" = Relationship(back_populates="product_orders")
    items: List["ProductOrderItem"] = Relationship(back_populates="order")


class ProductOrderItem(SQLModel, table=True):
    """Individual items in a product order."""
    __tablename__ = "product_order_items"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="product_orders.id")
    product_id: int = Field(foreign_key="products.id")
    
    # Item details
    quantity: int = Field(default=1)
    unit_price: float  # Price at time of order
    total_price: float  # quantity * unit_price
    
    # Product snapshot (in case product changes later)
    product_name: str
    product_sku: Optional[str] = None
    
    # Relationships
    order: ProductOrder = Relationship(back_populates="items")


# Pydantic models for API
class ProductOrderItemCreate(SQLModel):
    """Product order item creation."""
    product_id: int
    quantity: int = 1


class ProductOrderItemRead(SQLModel):
    """Product order item read."""
    id: int
    product_id: int
    quantity: int
    unit_price: float
    total_price: float
    product_name: str
    product_sku: Optional[str]


class ProductOrderCreate(SQLModel):
    """Product order creation."""
    shop_id: int
    customer_vehicle_id: Optional[int] = None
    items: List[ProductOrderItemCreate]
    pickup_date: Optional[datetime] = None
    notes: Optional[str] = None


class ProductOrderRead(ProductOrderBase):
    """Product order read model."""
    id: int
    items: List[ProductOrderItemRead] = []


class ProductOrderStatusUpdate(SQLModel):
    """Update order status."""
    status: OrderStatus
    notes: Optional[str] = None
