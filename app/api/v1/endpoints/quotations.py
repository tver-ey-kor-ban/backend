"""Quotation endpoints for shop estimates and customer approval."""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.db import get_session
from app.models.quotation import (
    Quotation, QuotationItem, QuotationCreate, QuotationRead,
    QuotationUpdate, QuotationApprovalRequest, QuotationStatus
)
from app.models.appointment import Appointment
from app.models.user import User
from app.core.security import get_current_user, TokenData
from app.services.shop_service import ShopService
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/quotations", tags=["quotations"])


# ==================== SHOP OWNER: CREATE/MANAGE QUOTATIONS ====================

@router.post("/shops/{shop_id}", response_model=QuotationRead, status_code=status.HTTP_201_CREATED)
def create_quotation(
    shop_id: int,
    quotation_data: QuotationCreate,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Create a new quotation for a customer (Shop owner/mechanic only)."""
    shop_service = ShopService(session)
    
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop members can create quotations"
        )
    
    # Validate appointment if provided
    customer_id = None
    if quotation_data.appointment_id:
        appointment = session.exec(
            select(Appointment).where(
                Appointment.id == quotation_data.appointment_id,
                Appointment.shop_id == shop_id
            )
        ).first()
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found"
            )
        customer_id = appointment.customer_id
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="appointment_id is required"
        )
    
    # Calculate totals from items
    labor_cost = quotation_data.labor_cost or 0.0
    parts_cost = quotation_data.parts_cost or 0.0
    tax_amount = quotation_data.tax_amount or 0.0
    discount_amount = quotation_data.discount_amount or 0.0
    
    items_total = sum(
        item.quantity * item.unit_price for item in quotation_data.items
    )
    total_amount = labor_cost + parts_cost + items_total + tax_amount - discount_amount
    
    # Create quotation
    quotation = Quotation(
        shop_id=shop_id,
        customer_id=customer_id,
        appointment_id=quotation_data.appointment_id,
        title=quotation_data.title,
        description=quotation_data.description,
        labor_cost=labor_cost,
        parts_cost=parts_cost,
        tax_amount=tax_amount,
        discount_amount=discount_amount,
        total_amount=total_amount,
        valid_until=quotation_data.valid_until,
        status=QuotationStatus.DRAFT
    )
    session.add(quotation)
    session.flush()
    
    # Create quotation items
    for item_data in quotation_data.items:
        total_price = item_data.quantity * item_data.unit_price
        item = QuotationItem(
            quotation_id=quotation.id,
            item_type=item_data.item_type,
            name=item_data.name,
            description=item_data.description,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            total_price=total_price
        )
        session.add(item)
    
    session.commit()
    session.refresh(quotation)
    
    return quotation


@router.get("/shops/{shop_id}", response_model=List[QuotationRead])
def get_shop_quotations(
    shop_id: int,
    status: Optional[QuotationStatus] = None,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get all quotations for a shop (Shop owner/mechanic only)."""
    shop_service = ShopService(session)
    
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop members can view quotations"
        )
    
    query = select(Quotation).where(Quotation.shop_id == shop_id)
    
    if status:
        query = query.where(Quotation.status == status)
    
    query = query.order_by(Quotation.created_at.desc())
    quotations = session.exec(query).all()
    
    # Load items for each quotation
    result = []
    for q in quotations:
        items = session.exec(
            select(QuotationItem).where(QuotationItem.quotation_id == q.id)
        ).all()
        q_dict = {
            "id": q.id,
            "shop_id": q.shop_id,
            "customer_id": q.customer_id,
            "appointment_id": q.appointment_id,
            "status": q.status,
            "title": q.title,
            "description": q.description,
            "labor_cost": q.labor_cost,
            "parts_cost": q.parts_cost,
            "tax_amount": q.tax_amount,
            "discount_amount": q.discount_amount,
            "total_amount": q.total_amount,
            "valid_until": q.valid_until,
            "approved_at": q.approved_at,
            "rejection_reason": q.rejection_reason,
            "created_at": q.created_at,
            "updated_at": q.updated_at,
            "items": items
        }
        result.append(q_dict)
    
    return result


@router.get("/shops/{shop_id}/{quotation_id}", response_model=QuotationRead)
def get_quotation_detail(
    shop_id: int,
    quotation_id: int,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get quotation details (Shop owner/mechanic only)."""
    shop_service = ShopService(session)
    
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop members can view quotations"
        )
    
    quotation = session.exec(
        select(Quotation).where(
            Quotation.id == quotation_id,
            Quotation.shop_id == shop_id
        )
    ).first()
    
    if not quotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quotation not found"
        )
    
    items = session.exec(
        select(QuotationItem).where(QuotationItem.quotation_id == quotation.id)
    ).all()
    
    return {
        "id": quotation.id,
        "shop_id": quotation.shop_id,
        "customer_id": quotation.customer_id,
        "appointment_id": quotation.appointment_id,
        "status": quotation.status,
        "title": quotation.title,
        "description": quotation.description,
        "labor_cost": quotation.labor_cost,
        "parts_cost": quotation.parts_cost,
        "tax_amount": quotation.tax_amount,
        "discount_amount": quotation.discount_amount,
        "total_amount": quotation.total_amount,
        "valid_until": quotation.valid_until,
        "approved_at": quotation.approved_at,
        "rejection_reason": quotation.rejection_reason,
        "created_at": quotation.created_at,
        "updated_at": quotation.updated_at,
        "items": items
    }


@router.put("/shops/{shop_id}/{quotation_id}", response_model=QuotationRead)
def update_quotation(
    shop_id: int,
    quotation_id: int,
    update_data: QuotationUpdate,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Update a quotation (Shop owner/mechanic only)."""
    shop_service = ShopService(session)
    
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop members can update quotations"
        )
    
    quotation = session.exec(
        select(Quotation).where(
            Quotation.id == quotation_id,
            Quotation.shop_id == shop_id
        )
    ).first()
    
    if not quotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quotation not found"
        )
    
    # Update fields
    if update_data.title is not None:
        quotation.title = update_data.title
    if update_data.description is not None:
        quotation.description = update_data.description
    if update_data.labor_cost is not None:
        quotation.labor_cost = update_data.labor_cost
    if update_data.parts_cost is not None:
        quotation.parts_cost = update_data.parts_cost
    if update_data.tax_amount is not None:
        quotation.tax_amount = update_data.tax_amount
    if update_data.discount_amount is not None:
        quotation.discount_amount = update_data.discount_amount
    if update_data.valid_until is not None:
        quotation.valid_until = update_data.valid_until
    if update_data.status is not None:
        quotation.status = update_data.status
    
    # Recalculate total if pricing changed
    items = session.exec(
        select(QuotationItem).where(QuotationItem.quotation_id == quotation.id)
    ).all()
    items_total = sum(item.total_price for item in items)
    quotation.total_amount = (
        quotation.labor_cost + quotation.parts_cost + items_total +
        quotation.tax_amount - quotation.discount_amount
    )
    
    quotation.updated_at = datetime.utcnow()
    session.commit()
    session.refresh(quotation)
    
    return quotation


@router.post("/shops/{shop_id}/{quotation_id}/send")
def send_quotation(
    shop_id: int,
    quotation_id: int,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Send quotation to customer (changes status to SENT)."""
    shop_service = ShopService(session)
    notification_service = NotificationService(session)
    
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop members can send quotations"
        )
    
    quotation = session.exec(
        select(Quotation).where(
            Quotation.id == quotation_id,
            Quotation.shop_id == shop_id
        )
    ).first()
    
    if not quotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quotation not found"
        )
    
    if quotation.status != QuotationStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot send quotation with status: {quotation.status}"
        )
    
    quotation.status = QuotationStatus.SENT
    quotation.updated_at = datetime.utcnow()
    session.commit()
    
    # Notify customer
    from app.models.notification import NotificationType
    notification_service.create_notification(
        user_id=quotation.customer_id,
        type=NotificationType.STATUS_UPDATE,
        title="New Quotation Received",
        message=f"You have received a new quotation: {quotation.title} - Total: ${quotation.total_amount:.2f}",
        data={
            "quotation_id": quotation.id,
            "title": quotation.title,
            "total_amount": quotation.total_amount
        }
    )
    
    return {
        "message": "Quotation sent to customer",
        "quotation_id": quotation.id,
        "status": quotation.status
    }


# ==================== CUSTOMER: VIEW/APPROVE QUOTATIONS ====================

@router.get("/my-quotations", response_model=List[QuotationRead])
def get_my_quotations(
    status: Optional[QuotationStatus] = None,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get all quotations for logged-in customer."""
    query = select(Quotation).where(Quotation.customer_id == current_user.user_id)
    
    if status:
        query = query.where(Quotation.status == status)
    
    query = query.order_by(Quotation.created_at.desc())
    quotations = session.exec(query).all()
    
    # Load items for each quotation
    result = []
    for q in quotations:
        items = session.exec(
            select(QuotationItem).where(QuotationItem.quotation_id == q.id)
        ).all()
        q_dict = {
            "id": q.id,
            "shop_id": q.shop_id,
            "customer_id": q.customer_id,
            "appointment_id": q.appointment_id,
            "status": q.status,
            "title": q.title,
            "description": q.description,
            "labor_cost": q.labor_cost,
            "parts_cost": q.parts_cost,
            "tax_amount": q.tax_amount,
            "discount_amount": q.discount_amount,
            "total_amount": q.total_amount,
            "valid_until": q.valid_until,
            "approved_at": q.approved_at,
            "rejection_reason": q.rejection_reason,
            "created_at": q.created_at,
            "updated_at": q.updated_at,
            "items": items
        }
        result.append(q_dict)
    
    return result


@router.get("/my-quotations/{quotation_id}")
def get_my_quotation_detail(
    quotation_id: int,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get specific quotation details for customer."""
    quotation = session.exec(
        select(Quotation).where(
            Quotation.id == quotation_id,
            Quotation.customer_id == current_user.user_id
        )
    ).first()
    
    if not quotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quotation not found"
        )
    
    items = session.exec(
        select(QuotationItem).where(QuotationItem.quotation_id == quotation.id)
    ).all()
    
    # Get shop info
    from app.models.shop import Shop
    shop = session.get(Shop, quotation.shop_id)
    
    return {
        "id": quotation.id,
        "shop": {
            "id": shop.id if shop else None,
            "name": shop.name if shop else "Unknown"
        },
        "appointment_id": quotation.appointment_id,
        "status": quotation.status,
        "title": quotation.title,
        "description": quotation.description,
        "labor_cost": quotation.labor_cost,
        "parts_cost": quotation.parts_cost,
        "tax_amount": quotation.tax_amount,
        "discount_amount": quotation.discount_amount,
        "total_amount": quotation.total_amount,
        "valid_until": quotation.valid_until,
        "approved_at": quotation.approved_at,
        "rejection_reason": quotation.rejection_reason,
        "created_at": quotation.created_at,
        "updated_at": quotation.updated_at,
        "items": items
    }


@router.post("/my-quotations/{quotation_id}/action")
def handle_quotation_action(
    quotation_id: int,
    action_request: QuotationApprovalRequest,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Customer approves or rejects a quotation."""
    notification_service = NotificationService(session)
    
    quotation = session.exec(
        select(Quotation).where(
            Quotation.id == quotation_id,
            Quotation.customer_id == current_user.user_id
        )
    ).first()
    
    if not quotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quotation not found"
        )
    
    if quotation.status not in [QuotationStatus.SENT, QuotationStatus.DRAFT]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot act on quotation with status: {quotation.status}"
        )
    
    if action_request.action == "approve":
        quotation.status = QuotationStatus.APPROVED
        quotation.approved_at = datetime.utcnow()
        quotation.updated_at = datetime.utcnow()
        session.commit()
        
        # Notify shop
        from app.models.notification import NotificationType
        from app.models.shop import UserShop
        
        customer = session.get(User, current_user.user_id)
        customer_name = customer.full_name if customer else "A customer"
        
        members = session.exec(
            select(UserShop).where(
                UserShop.shop_id == quotation.shop_id,
                UserShop.is_active
            )
        ).all()
        
        for member in members:
            notification_service.create_notification(
                user_id=member.user_id,
                type=NotificationType.STATUS_UPDATE,
                title="Quotation Approved",
                message=f"{customer_name} approved quotation: {quotation.title} - ${quotation.total_amount:.2f}",
                data={
                    "quotation_id": quotation.id,
                    "title": quotation.title,
                    "total_amount": quotation.total_amount
                }
            )
        
        return {
            "message": "Quotation approved successfully",
            "quotation_id": quotation.id,
            "status": quotation.status
        }
    
    elif action_request.action == "reject":
        quotation.status = QuotationStatus.REJECTED
        quotation.rejection_reason = action_request.rejection_reason
        quotation.updated_at = datetime.utcnow()
        session.commit()
        
        # Notify shop
        from app.models.notification import NotificationType
        from app.models.shop import UserShop
        
        customer = session.get(User, current_user.user_id)
        customer_name = customer.full_name if customer else "A customer"
        
        members = session.exec(
            select(UserShop).where(
                UserShop.shop_id == quotation.shop_id,
                UserShop.is_active
            )
        ).all()
        
        for member in members:
            notification_service.create_notification(
                user_id=member.user_id,
                type=NotificationType.STATUS_UPDATE,
                title="Quotation Rejected",
                message=f"{customer_name} rejected quotation: {quotation.title}",
                data={
                    "quotation_id": quotation.id,
                    "title": quotation.title,
                    "reason": action_request.rejection_reason
                }
            )
        
        return {
            "message": "Quotation rejected",
            "quotation_id": quotation.id,
            "status": quotation.status
        }
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Use 'approve' or 'reject'"
        )
