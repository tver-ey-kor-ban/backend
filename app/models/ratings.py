"""Rating models for products and services."""
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class ProductRating(SQLModel, table=True):
    """Customer ratings for products."""
    __tablename__ = "product_ratings"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    product_id: int = Field(foreign_key="products.id", index=True)
    customer_id: int = Field(foreign_key="users.id")
    order_id: Optional[int] = Field(default=None, foreign_key="product_orders.id")
    
    rating: int = Field(ge=1, le=5)  # 1-5 stars
    review: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class ProductRatingCreate(SQLModel):
    """Create product rating."""
    product_id: int
    order_id: Optional[int] = None
    rating: int
    review: Optional[str] = None


class ProductRatingRead(SQLModel):
    """Read product rating."""
    id: int
    product_id: int
    customer_id: int
    rating: int
    review: Optional[str]
    created_at: datetime


class ServiceRating(SQLModel, table=True):
    """Customer ratings for services."""
    __tablename__ = "service_ratings"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    service_id: int = Field(foreign_key="services.id", index=True)
    customer_id: int = Field(foreign_key="users.id")
    appointment_id: Optional[int] = Field(default=None, foreign_key="appointments.id")
    
    rating: int = Field(ge=1, le=5)  # 1-5 stars
    review: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class ServiceRatingCreate(SQLModel):
    """Create service rating."""
    service_id: int
    appointment_id: Optional[int] = None
    rating: int
    review: Optional[str] = None


class ServiceRatingRead(SQLModel):
    """Read service rating."""
    id: int
    service_id: int
    customer_id: int
    rating: int
    review: Optional[str]
    created_at: datetime


class RatingSummary(SQLModel):
    """Summary of ratings for a product or service."""
    average_rating: float
    total_ratings: int
    five_star: int
    four_star: int
    three_star: int
    two_star: int
    one_star: int
