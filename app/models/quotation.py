"""Quotation models for repair shop estimates."""
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from enum import Enum
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from app.models.user import User


class QuotationStatus(str, Enum):
    """Quotation status enum."""
    DRAFT = "draft"
    SENT = "sent"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class QuotationBase(SQLModel):
    """Base quotation model."""
    shop_id: int = Field(foreign_key="shops.id")
    customer_id: int = Field(foreign_key="users.id")
    appointment_id: Optional[int] = Field(default=None, foreign_key="appointments.id")
    
    # Quotation info
    status: QuotationStatus = QuotationStatus.DRAFT
    title: str  # e.g., "Engine Repair Estimate"
    description: Optional[str] = None
    
    # Pricing
    labor_cost: float = Field(default=0.0)
    parts_cost: float = Field(default=0.0)
    tax_amount: float = Field(default=0.0)
    discount_amount: float = Field(default=0.0)
    total_amount: float = Field(default=0.0)
    
    # Validity
    valid_until: Optional[datetime] = None
    
    # Approval
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Quotation(QuotationBase, table=True):
    """Quotation database model."""
    __tablename__ = "quotations"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Relationships
    customer: "User" = Relationship(back_populates="quotations")
    items: List["QuotationItem"] = Relationship(back_populates="quotation")


class QuotationItem(SQLModel, table=True):
    """Individual line items in a quotation."""
    __tablename__ = "quotation_items"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    quotation_id: int = Field(foreign_key="quotations.id")
    
    # Item info
    item_type: str  # "labor", "part", "service", "other"
    name: str
    description: Optional[str] = None
    
    # Pricing
    quantity: float = Field(default=1.0)
    unit_price: float
    total_price: float
    
    # Relationships
    quotation: Quotation = Relationship(back_populates="items")


# Pydantic models for API
class QuotationItemCreate(SQLModel):
    """Quotation item creation."""
    item_type: str
    name: str
    description: Optional[str] = None
    quantity: float = 1.0
    unit_price: float


class QuotationItemRead(SQLModel):
    """Quotation item read."""
    id: int
    item_type: str
    name: str
    description: Optional[str]
    quantity: float
    unit_price: float
    total_price: float


class QuotationCreate(SQLModel):
    """Quotation creation."""
    shop_id: int
    appointment_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    items: List[QuotationItemCreate]
    labor_cost: float = 0.0
    parts_cost: float = 0.0
    tax_amount: float = 0.0
    discount_amount: float = 0.0
    valid_until: Optional[datetime] = None


class QuotationRead(QuotationBase):
    """Quotation read model."""
    id: int
    items: List[QuotationItemRead] = []


class QuotationUpdate(SQLModel):
    """Update quotation (shop owner)."""
    title: Optional[str] = None
    description: Optional[str] = None
    items: Optional[List[QuotationItemCreate]] = None
    labor_cost: Optional[float] = None
    parts_cost: Optional[float] = None
    tax_amount: Optional[float] = None
    discount_amount: Optional[float] = None
    valid_until: Optional[datetime] = None
    status: Optional[QuotationStatus] = None


class QuotationApprovalRequest(SQLModel):
    """Customer approval/rejection request."""
    action: str  # "approve" or "reject"
    rejection_reason: Optional[str] = None
