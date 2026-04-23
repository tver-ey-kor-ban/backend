"""Chat/Support models for customer-shop communication."""
from datetime import datetime
from typing import Optional, List
from enum import Enum
from sqlmodel import Field, SQLModel, Relationship

class ChatRoomType(str, Enum):
    """Chat room type enum."""
    APPOINTMENT = "appointment"
    ORDER = "order"
    GENERAL = "general"


class ChatMessageType(str, Enum):
    """Chat message type enum."""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"


class ChatRoom(SQLModel, table=True):
    """Chat room for customer-shop communication."""
    __tablename__ = "chat_rooms"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Room info
    shop_id: int = Field(foreign_key="shops.id")
    customer_id: int = Field(foreign_key="users.id")
    room_type: ChatRoomType = ChatRoomType.GENERAL
    
    # Link to appointment or order
    appointment_id: Optional[int] = Field(default=None, foreign_key="appointments.id")
    product_order_id: Optional[int] = Field(default=None, foreign_key="product_orders.id")
    
    # Room status
    is_active: bool = True
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    # Relationships
    messages: List["ChatMessage"] = Relationship(back_populates="room")


class ChatMessage(SQLModel, table=True):
    """Individual chat messages."""
    __tablename__ = "chat_messages"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: int = Field(foreign_key="chat_rooms.id")
    
    # Sender
    sender_id: int = Field(foreign_key="users.id")
    
    # Message info
    message_type: ChatMessageType = ChatMessageType.TEXT
    content: str
    attachment_url: Optional[str] = None
    
    # Read status
    is_read: bool = False
    read_at: Optional[datetime] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    room: ChatRoom = Relationship(back_populates="messages")


# Pydantic models for API
class ChatMessageCreate(SQLModel):
    """Create chat message."""
    content: str
    message_type: ChatMessageType = ChatMessageType.TEXT
    attachment_url: Optional[str] = None


class ChatMessageRead(SQLModel):
    """Read chat message."""
    id: int
    sender_id: int
    message_type: ChatMessageType
    content: str
    attachment_url: Optional[str]
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime


class ChatRoomCreate(SQLModel):
    """Create chat room."""
    shop_id: int
    room_type: ChatRoomType = ChatRoomType.GENERAL
    appointment_id: Optional[int] = None
    product_order_id: Optional[int] = None


class ChatRoomRead(SQLModel):
    """Read chat room."""
    id: int
    shop_id: int
    customer_id: int
    room_type: ChatRoomType
    appointment_id: Optional[int]
    product_order_id: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    messages: List[ChatMessageRead] = []
    unread_count: int = 0


class ChatRoomSummary(SQLModel):
    """Summary of chat room for list view."""
    id: int
    shop_id: int
    customer_id: int
    room_type: ChatRoomType
    appointment_id: Optional[int]
    product_order_id: Optional[int]
    is_active: bool
    last_message: Optional[ChatMessageRead] = None
    unread_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime]
