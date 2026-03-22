"""Appointment and Service History models for customers."""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from enum import Enum
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from app.models.user import User


class AppointmentStatus(str, Enum):
    """Appointment status enum."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AppointmentBase(SQLModel):
    """Base appointment model."""
    shop_id: int = Field(foreign_key="shops.id")
    customer_id: int = Field(foreign_key="users.id")
    service_id: Optional[int] = Field(default=None, foreign_key="services.id")
    customer_vehicle_id: Optional[int] = Field(default=None, foreign_key="customer_vehicles.id")
    vehicle_info: Optional[str] = None  # "Toyota Camry 2020" (snapshot or manual entry)
    appointment_date: datetime
    notes: Optional[str] = None
    status: AppointmentStatus = AppointmentStatus.PENDING
    
    # Price calculation fields
    service_price: Optional[float] = Field(default=0.0)  # Service price at booking time
    mobile_service_fee: Optional[float] = Field(default=0.0)  # Mobile service fee
    discount_amount: Optional[float] = Field(default=0.0)  # Discount applied
    tax_amount: Optional[float] = Field(default=0.0)  # Tax amount
    total_amount: Optional[float] = Field(default=0.0)  # Final total


class Appointment(AppointmentBase, table=True):
    """Appointment database model."""
    __tablename__ = "appointments"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    # Relationships
    customer: "User" = Relationship(back_populates="appointments")


class AppointmentCreate(AppointmentBase):
    """Appointment creation model."""
    pass


class AppointmentRead(AppointmentBase):
    """Appointment read model."""
    id: int
    created_at: datetime


class ServiceHistory(SQLModel, table=True):
    """Service history for customers."""
    __tablename__ = "service_history"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    shop_id: int = Field(foreign_key="shops.id")
    customer_id: int = Field(foreign_key="users.id")
    appointment_id: Optional[int] = Field(default=None, foreign_key="appointments.id")
    service_name: str  # Snapshot of service name
    service_description: Optional[str] = None
    price: float
    completed_date: datetime
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ServiceHistoryCreate(SQLModel):
    """Service history creation model."""
    shop_id: int
    customer_id: int
    appointment_id: Optional[int] = None
    service_name: str
    service_description: Optional[str] = None
    price: float
    completed_date: datetime
    notes: Optional[str] = None


class ServiceHistoryRead(SQLModel):
    """Service history read model."""
    id: int
    shop_id: int
    customer_id: int
    service_name: str
    price: float
    completed_date: datetime
    notes: Optional[str]
