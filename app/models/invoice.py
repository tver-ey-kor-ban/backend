"""Invoice models for repair shop billing."""
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from enum import Enum
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from app.models.user import User


class InvoiceStatus(str, Enum):
    """Invoice status enum."""
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    PARTIALLY_PAID = "partially_paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class PaymentMethod(str, Enum):
    """Payment method enum."""
    CASH = "cash"
    CARD = "card"
    TRANSFER = "transfer"
    MOBILE_PAYMENT = "mobile_payment"
    OTHER = "other"


class InvoiceBase(SQLModel):
    """Base invoice model."""
    shop_id: int = Field(foreign_key="shops.id")
    customer_id: int = Field(foreign_key="users.id")
    
    # Link to appointment or order
    appointment_id: Optional[int] = Field(default=None, foreign_key="appointments.id")
    product_order_id: Optional[int] = Field(default=None, foreign_key="product_orders.id")
    quotation_id: Optional[int] = Field(default=None, foreign_key="quotations.id")
    
    # Invoice info
    invoice_number: str = Field(index=True, unique=True)
    status: InvoiceStatus = InvoiceStatus.DRAFT
    
    # Pricing breakdown
    labor_cost: float = Field(default=0.0)
    parts_cost: float = Field(default=0.0)
    service_cost: float = Field(default=0.0)
    tax_amount: float = Field(default=0.0)
    discount_amount: float = Field(default=0.0)
    total_amount: float = Field(default=0.0)
    amount_paid: float = Field(default=0.0)
    
    # Due date
    due_date: Optional[datetime] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None


class Invoice(InvoiceBase, table=True):
    """Invoice database model."""
    __tablename__ = "invoices"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Relationships
    customer: "User" = Relationship(back_populates="invoices")
    items: List["InvoiceItem"] = Relationship(back_populates="invoice")
    payments: List["Payment"] = Relationship(back_populates="invoice")


class InvoiceItem(SQLModel, table=True):
    """Individual line items in an invoice."""
    __tablename__ = "invoice_items"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    invoice_id: int = Field(foreign_key="invoices.id")
    
    # Item info
    item_type: str  # "labor", "part", "service", "tax", "discount", "other"
    name: str
    description: Optional[str] = None
    
    # Pricing
    quantity: float = Field(default=1.0)
    unit_price: float
    total_price: float
    
    # Relationships
    invoice: Invoice = Relationship(back_populates="items")


class Payment(SQLModel, table=True):
    """Payment record for invoices."""
    __tablename__ = "payments"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    invoice_id: int = Field(foreign_key="invoices.id")
    
    # Payment info
    amount: float
    method: PaymentMethod
    reference: Optional[str] = None  # Transaction ID, check number, etc.
    notes: Optional[str] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    invoice: Invoice = Relationship(back_populates="payments")


# Pydantic models for API
class InvoiceItemCreate(SQLModel):
    """Invoice item creation."""
    item_type: str
    name: str
    description: Optional[str] = None
    quantity: float = 1.0
    unit_price: float


class InvoiceItemRead(SQLModel):
    """Invoice item read."""
    id: int
    item_type: str
    name: str
    description: Optional[str]
    quantity: float
    unit_price: float
    total_price: float


class PaymentCreate(SQLModel):
    """Payment creation."""
    amount: float
    method: PaymentMethod
    reference: Optional[str] = None
    notes: Optional[str] = None


class PaymentRead(SQLModel):
    """Payment read."""
    id: int
    amount: float
    method: PaymentMethod
    reference: Optional[str]
    notes: Optional[str]
    created_at: datetime


class InvoiceCreate(SQLModel):
    """Invoice creation."""
    shop_id: int
    customer_id: int
    appointment_id: Optional[int] = None
    product_order_id: Optional[int] = None
    quotation_id: Optional[int] = None
    invoice_number: str
    items: List[InvoiceItemCreate]
    labor_cost: float = 0.0
    parts_cost: float = 0.0
    service_cost: float = 0.0
    tax_amount: float = 0.0
    discount_amount: float = 0.0
    total_amount: float
    due_date: Optional[datetime] = None


class InvoiceRead(InvoiceBase):
    """Invoice read model."""
    id: int
    items: List[InvoiceItemRead] = []
    payments: List[PaymentRead] = []


class InvoiceUpdate(SQLModel):
    """Update invoice (shop owner)."""
    status: Optional[InvoiceStatus] = None
    due_date: Optional[datetime] = None
    items: Optional[List[InvoiceItemCreate]] = None
    labor_cost: Optional[float] = None
    parts_cost: Optional[float] = None
    service_cost: Optional[float] = None
    tax_amount: Optional[float] = None
    discount_amount: Optional[float] = None
    total_amount: Optional[float] = None
