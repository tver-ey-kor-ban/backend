"""Repair progress tracking models."""
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from enum import Enum
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from app.models.user import User


class RepairStage(str, Enum):
    """Repair stage enum."""
    RECEIVED = "received"
    DIAGNOSING = "diagnosing"
    WAITING_PARTS = "waiting_parts"
    IN_PROGRESS = "in_progress"
    QUALITY_CHECK = "quality_check"
    READY_FOR_PICKUP = "ready_for_pickup"
    COMPLETED = "completed"


class RepairProgressBase(SQLModel):
    """Base repair progress model."""
    shop_id: int = Field(foreign_key="shops.id")
    customer_id: int = Field(foreign_key="users.id")
    appointment_id: int = Field(foreign_key="appointments.id")
    
    # Current stage
    stage: RepairStage = RepairStage.RECEIVED
    
    # Progress info
    description: Optional[str] = None
    notes: Optional[str] = None
    
    # Estimated completion
    estimated_completion: Optional[datetime] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class RepairProgress(RepairProgressBase, table=True):
    """Repair progress database model."""
    __tablename__ = "repair_progress"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Relationships
    customer: "User" = Relationship(back_populates="repair_progress_records")
    updates: List["RepairProgressUpdate"] = Relationship(back_populates="repair_progress")


class RepairProgressUpdate(SQLModel, table=True):
    """Individual updates to repair progress."""
    __tablename__ = "repair_progress_updates"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    repair_progress_id: int = Field(foreign_key="repair_progress.id")
    
    # Who made the update
    updated_by: int = Field(foreign_key="users.id")
    
    # Update info
    from_stage: Optional[str] = None
    to_stage: str
    note: Optional[str] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    repair_progress: RepairProgress = Relationship(back_populates="updates")


# Pydantic models for API
class RepairProgressUpdateCreate(SQLModel):
    """Create repair progress update."""
    to_stage: str
    note: Optional[str] = None
    estimated_completion: Optional[datetime] = None


class RepairProgressUpdateRead(SQLModel):
    """Read repair progress update."""
    id: int
    updated_by: int
    from_stage: Optional[str]
    to_stage: str
    note: Optional[str]
    created_at: datetime


class RepairProgressCreate(SQLModel):
    """Create repair progress record."""
    shop_id: int
    appointment_id: int
    stage: RepairStage = RepairStage.RECEIVED
    description: Optional[str] = None
    notes: Optional[str] = None
    estimated_completion: Optional[datetime] = None


class RepairProgressRead(RepairProgressBase):
    """Read repair progress."""
    id: int
    updates: List[RepairProgressUpdateRead] = []


class RepairProgressUpdateRequest(SQLModel):
    """Request to update repair stage."""
    stage: RepairStage
    note: Optional[str] = None
    estimated_completion: Optional[datetime] = None
