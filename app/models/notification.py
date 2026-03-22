"""Notification models for booking alerts and updates."""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from enum import Enum
from sqlmodel import Field, SQLModel

if TYPE_CHECKING:
    pass


class NotificationType(str, Enum):
    """Notification type enum."""
    NEW_BOOKING = "new_booking"           # New service booking received (for shop)
    NEW_PRODUCT_ORDER = "new_product_order"  # New product order received (for shop)
    BOOKING_CONFIRMED = "booking_confirmed"  # Booking accepted (for customer)
    BOOKING_REJECTED = "booking_rejected"    # Booking rejected (for customer)
    BOOKING_CANCELLED = "booking_cancelled"  # Booking cancelled
    ORDER_CONFIRMED = "order_confirmed"   # Product order confirmed (for customer)
    ORDER_REJECTED = "order_rejected"     # Product order rejected (for customer)
    ORDER_CANCELLED = "order_cancelled"   # Product order cancelled
    ORDER_READY = "order_ready"           # Product order ready for pickup
    STATUS_UPDATE = "status_update"       # Status changed
    REMINDER = "reminder"                 # Appointment reminder


class NotificationStatus(str, Enum):
    """Notification status enum."""
    UNREAD = "unread"
    READ = "read"
    ARCHIVED = "archived"


class Notification(SQLModel, table=True):
    """Notification database model."""
    __tablename__ = "notifications"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Who receives this notification
    user_id: int = Field(foreign_key="users.id", index=True)
    
    # Related booking/order
    appointment_id: Optional[int] = Field(default=None, foreign_key="appointments.id")
    product_order_id: Optional[int] = Field(default=None, foreign_key="product_orders.id")
    
    # Notification content
    type: NotificationType
    title: str
    message: str
    status: NotificationStatus = NotificationStatus.UNREAD
    
    # Additional data (JSON)
    data: Optional[str] = None  # JSON string with extra info
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    read_at: Optional[datetime] = None


class NotificationCreate(SQLModel):
    """Notification creation model."""
    user_id: int
    type: NotificationType
    title: str
    message: str
    appointment_id: Optional[int] = None
    product_order_id: Optional[int] = None
    data: Optional[str] = None


class NotificationRead(SQLModel):
    """Notification read model."""
    id: int
    type: NotificationType
    title: str
    message: str
    status: NotificationStatus
    appointment_id: Optional[int]
    product_order_id: Optional[int]
    created_at: datetime
    read_at: Optional[datetime]


class BookingAction(str, Enum):
    """Booking action enum for mechanics."""
    ACCEPT = "accept"
    REJECT = "reject"


class BookingActionRequest(SQLModel):
    """Request model for mechanic to accept/reject booking."""
    action: BookingAction
    reason: Optional[str] = None  # Reason for rejection
    estimated_start_time: Optional[datetime] = None  # When mechanic will start (for accept)
    notes: Optional[str] = None  # Additional notes


class BookingActionResponse(SQLModel):
    """Response after mechanic action."""
    success: bool
    message: str
    appointment_id: int
    new_status: str
    customer_notified: bool
