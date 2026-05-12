"""Repair progress tracking endpoints."""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.db import get_session
from app.models.repair_progress import (
    RepairProgress, RepairProgressUpdate, RepairProgressCreate,
    RepairProgressRead, RepairStage, RepairProgressUpdateRequest
)
from app.models.appointment import Appointment, AppointmentStatus
from app.models.user import User
from app.core.security import get_current_user, TokenData
from app.services.shop_service import ShopService
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/repair-progress", tags=["repair-progress"])


# ==================== SHOP: MANAGE REPAIR PROGRESS ====================

@router.post("/shops/{shop_id}", response_model=RepairProgressRead, status_code=status.HTTP_201_CREATED)
def create_repair_progress(
    shop_id: int,
    progress_data: RepairProgressCreate,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Create a repair progress record for an appointment (Shop only)."""
    shop_service = ShopService(session)
    
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop members can create repair progress records"
        )
    
    # Validate appointment
    appointment = session.exec(
        select(Appointment).where(
            Appointment.id == progress_data.appointment_id,
            Appointment.shop_id == shop_id
        )
    ).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    # Check if progress record already exists
    existing = session.exec(
        select(RepairProgress).where(
            RepairProgress.appointment_id == progress_data.appointment_id
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Repair progress record already exists for this appointment"
        )
    
    # Create progress record
    progress = RepairProgress(
        shop_id=shop_id,
        customer_id=appointment.customer_id,
        appointment_id=progress_data.appointment_id,
        stage=progress_data.stage,
        description=progress_data.description,
        notes=progress_data.notes,
        estimated_completion=progress_data.estimated_completion
    )
    session.add(progress)
    session.flush()
    
    # Create initial update
    update = RepairProgressUpdate(
        repair_progress_id=progress.id,
        updated_by=current_user.user_id,
        to_stage=progress_data.stage.value,
        note=f"Repair progress started: {progress_data.description or ''}"
    )
    session.add(update)
    session.commit()
    session.refresh(progress)
    
    # Notify customer
    notification_service = NotificationService(session)
    from app.models.notification import NotificationType
    from app.models.shop import Shop
    
    shop = session.get(Shop, shop_id)
    shop_name = shop.name if shop else "The shop"
    
    notification_service.create_notification(
        user_id=appointment.customer_id,
        type=NotificationType.STATUS_UPDATE,
        title="Repair Progress Updated",
        message=f"{shop_name} has started tracking your repair progress.",
        appointment_id=appointment.id,
        data={
            "stage": progress.stage.value,
            "description": progress.description
        }
    )
    
    return progress


@router.put("/shops/{shop_id}/{progress_id}")
def update_repair_stage(
    shop_id: int,
    progress_id: int,
    update_request: RepairProgressUpdateRequest,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Update repair progress stage (Shop only)."""
    shop_service = ShopService(session)
    notification_service = NotificationService(session)
    
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop members can update repair progress"
        )
    
    progress = session.exec(
        select(RepairProgress).where(
            RepairProgress.id == progress_id,
            RepairProgress.shop_id == shop_id
        )
    ).first()
    
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repair progress record not found"
        )
    
    old_stage = progress.stage.value
    
    # Update progress
    progress.stage = update_request.stage
    if update_request.estimated_completion is not None:
        progress.estimated_completion = update_request.estimated_completion
    progress.updated_at = datetime.utcnow()
    
    # Create update record
    update = RepairProgressUpdate(
        repair_progress_id=progress.id,
        updated_by=current_user.user_id,
        from_stage=old_stage,
        to_stage=update_request.stage.value,
        note=update_request.note
    )
    session.add(update)
    session.commit()
    session.refresh(progress)
    
    # If completed, update appointment status too
    if update_request.stage == RepairStage.COMPLETED:
        appointment = session.get(Appointment, progress.appointment_id)
        if appointment:
            appointment.status = AppointmentStatus.COMPLETED
            appointment.updated_at = datetime.utcnow()
            session.commit()
    
    # Notify customer
    from app.models.notification import NotificationType
    from app.models.shop import Shop
    
    shop = session.get(Shop, shop_id)
    shop_name = shop.name if shop else "The shop"
    
    stage_messages = {
        RepairStage.RECEIVED: "Your vehicle has been received.",
        RepairStage.DIAGNOSING: "Your vehicle is being diagnosed.",
        RepairStage.WAITING_PARTS: "Waiting for parts to arrive.",
        RepairStage.IN_PROGRESS: "Repair work is in progress.",
        RepairStage.QUALITY_CHECK: "Quality check in progress.",
        RepairStage.READY_FOR_PICKUP: "Your vehicle is ready for pickup!",
        RepairStage.COMPLETED: "Your repair has been completed."
    }
    
    message = stage_messages.get(
        update_request.stage,
        f"Repair stage updated to: {update_request.stage.value}"
    )
    
    notification_service.create_notification(
        user_id=progress.customer_id,
        type=NotificationType.STATUS_UPDATE,
        title="Repair Progress Update",
        message=f"{shop_name}: {message}",
        appointment_id=progress.appointment_id,
        data={
            "stage": update_request.stage.value,
            "note": update_request.note,
            "estimated_completion": progress.estimated_completion.isoformat() if progress.estimated_completion else None
        }
    )
    
    return {
        "message": "Repair progress updated",
        "progress_id": progress.id,
        "new_stage": progress.stage.value,
        "previous_stage": old_stage,
        "updated_at": progress.updated_at
    }


@router.get("/shops/{shop_id}")
def get_shop_repair_progress(
    shop_id: int,
    stage: Optional[RepairStage] = None,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get all repair progress records for a shop (Shop only)."""
    shop_service = ShopService(session)
    
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop members can view repair progress"
        )
    
    query = select(RepairProgress).where(RepairProgress.shop_id == shop_id)
    
    if stage:
        query = query.where(RepairProgress.stage == stage)
    
    query = query.order_by(RepairProgress.updated_at.desc())
    progress_records = session.exec(query).all()
    
    # Enrich with customer info
    result = []
    for progress in progress_records:
        customer = session.get(User, progress.customer_id)

        result.append({
            "id": progress.id,
            "appointment_id": progress.appointment_id,
            "customer": {
                "id": progress.customer_id,
                "name": customer.full_name if customer else "Unknown"
            },
            "stage": progress.stage.value,
            "description": progress.description,
            "estimated_completion": progress.estimated_completion,
            "created_at": progress.created_at,
            "updated_at": progress.updated_at
        })
    
    return result


# ==================== CUSTOMER: VIEW REPAIR PROGRESS ====================

@router.get("/my-repairs")
def get_my_repair_progress(
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get all repair progress records for logged-in customer."""
    progress_records = session.exec(
        select(RepairProgress).where(
            RepairProgress.customer_id == current_user.user_id
        ).order_by(RepairProgress.updated_at.desc())
    ).all()
    
    result = []
    for progress in progress_records:
        # Get updates
        updates = session.exec(
            select(RepairProgressUpdate).where(
                RepairProgressUpdate.repair_progress_id == progress.id
            ).order_by(RepairProgressUpdate.created_at.desc())
        ).all()
        
        # Get shop info
        from app.models.shop import Shop
        shop = session.get(Shop, progress.shop_id)
        
        # Get appointment info
        appointment = session.get(Appointment, progress.appointment_id)
        
        result.append({
            "id": progress.id,
            "shop": {
                "id": progress.shop_id,
                "name": shop.name if shop else "Unknown"
            },
            "appointment_id": progress.appointment_id,
            "vehicle_info": appointment.vehicle_info if appointment else None,
            "stage": progress.stage.value,
            "description": progress.description,
            "notes": progress.notes,
            "estimated_completion": progress.estimated_completion,
            "created_at": progress.created_at,
            "updated_at": progress.updated_at,
            "updates": [
                {
                    "id": u.id,
                    "from_stage": u.from_stage,
                    "to_stage": u.to_stage,
                    "note": u.note,
                    "created_at": u.created_at
                }
                for u in updates
            ]
        })
    
    return result


@router.get("/my-repairs/{progress_id}")
def get_my_repair_detail(
    progress_id: int,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get specific repair progress details for customer."""
    progress = session.exec(
        select(RepairProgress).where(
            RepairProgress.id == progress_id,
            RepairProgress.customer_id == current_user.user_id
        )
    ).first()
    
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repair progress not found"
        )
    
    # Get updates
    updates = session.exec(
        select(RepairProgressUpdate).where(
            RepairProgressUpdate.repair_progress_id == progress.id
        ).order_by(RepairProgressUpdate.created_at.desc())
    ).all()
    
    # Get shop info
    from app.models.shop import Shop
    shop = session.get(Shop, progress.shop_id)
    
    # Get appointment info
    appointment = session.get(Appointment, progress.appointment_id)
    
    return {
        "id": progress.id,
        "shop": {
            "id": progress.shop_id,
            "name": shop.name if shop else "Unknown"
        },
        "appointment_id": progress.appointment_id,
        "vehicle_info": appointment.vehicle_info if appointment else None,
        "stage": progress.stage.value,
        "description": progress.description,
        "notes": progress.notes,
        "estimated_completion": progress.estimated_completion,
        "created_at": progress.created_at,
        "updated_at": progress.updated_at,
        "updates": [
            {
                "id": u.id,
                "from_stage": u.from_stage,
                "to_stage": u.to_stage,
                "note": u.note,
                "created_at": u.created_at
            }
            for u in updates
        ]
    }
