"""Customer Vehicle models for storing customer's vehicle information."""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from app.models.user import User


class CustomerVehicleBase(SQLModel):
    """Base customer vehicle model."""
    # Vehicle identification
    make: str = Field(index=True)  # Toyota, Honda
    model: str = Field(index=True)  # Camry, Civic
    year: int = Field(index=True)  # 2020, 2021
    
    # Optional detailed info
    engine: Optional[str] = None  # 2.5L V6
    fuel_type: Optional[str] = None  # gasoline, diesel, hybrid
    transmission: Optional[str] = None  # automatic, manual
    
    # Vehicle identifiers
    license_plate: Optional[str] = None  # ABC-123
    vin: Optional[str] = None  # Vehicle Identification Number
    color: Optional[str] = None
    
    # Customer info
    nickname: Optional[str] = None  # "My Car", "Dad's Truck"
    is_primary: bool = False  # Default vehicle for customer
    
    # Metadata
    is_active: bool = True


class CustomerVehicle(CustomerVehicleBase, table=True):
    """Customer vehicle database model."""
    __tablename__ = "customer_vehicles"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    # Relationships
    customer: "User" = Relationship(back_populates="vehicles")


class CustomerVehicleCreate(CustomerVehicleBase):
    """Customer vehicle creation model."""
    pass


class CustomerVehicleRead(CustomerVehicleBase):
    """Customer vehicle read model."""
    id: int
    customer_id: int
    created_at: datetime


class CustomerVehicleUpdate(SQLModel):
    """Customer vehicle update model (all fields optional)."""
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    engine: Optional[str] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    license_plate: Optional[str] = None
    vin: Optional[str] = None
    color: Optional[str] = None
    nickname: Optional[str] = None
    is_primary: Optional[bool] = None
    is_active: Optional[bool] = None


# Vehicle filter request from customer's vehicle
class VehicleFilterByCustomer(SQLModel):
    """Filter products by customer's saved vehicle."""
    customer_vehicle_id: int
    category_id: Optional[int] = None
