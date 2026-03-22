"""Mechanic performance tracking models."""
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class MechanicPerformance(SQLModel, table=True):
    """Performance record for each mechanic assignment."""
    __tablename__ = "mechanic_performances"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Who did the work
    mechanic_id: int = Field(foreign_key="users.id", index=True)
    shop_id: int = Field(foreign_key="shops.id", index=True)
    
    # What was done
    appointment_id: Optional[int] = Field(default=None, foreign_key="appointments.id")
    service_name: str  # Snapshot of service
    
    # Performance metrics
    completed_date: datetime
    revenue_generated: float = Field(default=0.0)  # Service price + products
    service_rating: Optional[int] = Field(default=None)  # 1-5 stars from customer
    customer_feedback: Optional[str] = None
    
    # Time tracking
    estimated_duration: Optional[int] = None  # Minutes
    actual_duration: Optional[int] = None  # Minutes
    
    # Status
    is_completed: bool = Field(default=True)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MechanicPerformanceCreate(SQLModel):
    """Create mechanic performance record."""
    mechanic_id: int
    shop_id: int
    appointment_id: Optional[int] = None
    service_name: str
    completed_date: datetime
    revenue_generated: float = 0.0
    estimated_duration: Optional[int] = None
    actual_duration: Optional[int] = None


class MechanicPerformanceUpdate(SQLModel):
    """Update mechanic performance record."""
    service_rating: Optional[int] = None
    customer_feedback: Optional[str] = None
    actual_duration: Optional[int] = None


class MechanicPerformanceRead(SQLModel):
    """Read mechanic performance record."""
    id: int
    mechanic_id: int
    shop_id: int
    appointment_id: Optional[int]
    service_name: str
    completed_date: datetime
    revenue_generated: float
    service_rating: Optional[int]
    customer_feedback: Optional[str]
    estimated_duration: Optional[int]
    actual_duration: Optional[int]
    created_at: datetime


class MechanicRating(SQLModel, table=True):
    """Customer ratings for mechanics."""
    __tablename__ = "mechanic_ratings"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    mechanic_id: int = Field(foreign_key="users.id", index=True)
    customer_id: int = Field(foreign_key="users.id")
    appointment_id: int = Field(foreign_key="appointments.id")
    
    rating: int = Field(ge=1, le=5)  # 1-5 stars
    review: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MechanicRatingCreate(SQLModel):
    """Create mechanic rating."""
    mechanic_id: int
    appointment_id: int
    rating: int
    review: Optional[str] = None


class MechanicRatingRead(SQLModel):
    """Read mechanic rating."""
    id: int
    mechanic_id: int
    customer_id: int
    appointment_id: int
    rating: int
    review: Optional[str]
    created_at: datetime
