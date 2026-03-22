"""Customer endpoints for browsing, booking appointments, and viewing service history."""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select

from app.db import get_session
from app.models.appointment import Appointment, AppointmentCreate, AppointmentRead, AppointmentStatus, ServiceHistory
from app.models.shop import UserShop
from app.models.user import User
from app.core.security import get_current_user, TokenData

router = APIRouter(prefix="/customers", tags=["customers"])


# ==================== PUBLIC BROWSING (No login required) ====================

@router.get("/shops/{shop_id}/browse/products")
def browse_products(
    shop_id: int,
    category_id: Optional[int] = None,
    q: Optional[str] = Query(None, description="Search query"),
    session: Session = Depends(get_session)
):
    """Browse products in a shop (PUBLIC - no login required)."""
    from app.models.product import Product
    
    query = select(Product).where(
        Product.shop_id == shop_id,
        Product.is_active
    )
    
    if category_id:
        query = query.where(Product.category_id == category_id)
    
    if q:
        query = query.where(
            Product.name.ilike(f"%{q}%") | 
            Product.description.ilike(f"%{q}%")
        )
    
    products = session.exec(query).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "price": p.price,
            "image_url": p.image_url,
            "thumbnail_url": p.thumbnail_url
        }
        for p in products
    ]


@router.get("/shops/{shop_id}/browse/services")
def browse_services(
    shop_id: int,
    session: Session = Depends(get_session)
):
    """Browse services in a shop (PUBLIC - no login required)."""
    from app.models.product import Service
    
    services = session.exec(
        select(Service).where(
            Service.shop_id == shop_id,
            Service.is_active
        )
    ).all()
    
    return [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "price": s.price,
            "duration_minutes": s.duration_minutes,
            "image_url": s.image_url
        }
        for s in services
    ]


@router.get("/shops/{shop_id}/browse/shop-info")
def browse_shop_info(
    shop_id: int,
    session: Session = Depends(get_session)
):
    """Get public shop information (PUBLIC - no login required)."""
    from app.models.shop import Shop
    
    shop = session.get(Shop, shop_id)
    if not shop or not shop.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found"
        )
    
    return {
        "id": shop.id,
        "name": shop.name,
        "description": shop.description,
        "address": shop.address,
        "phone": shop.phone,
        "email": shop.email
    }


# ==================== CUSTOMER BOOKING (Login required) ====================

@router.post("/appointments", response_model=AppointmentRead, status_code=status.HTTP_201_CREATED)
def book_appointment(
    appointment_data: AppointmentCreate,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """[DEPRECATED] Use /product-orders/unified-booking instead.
    
    Book an appointment (Customer must be logged in).
    """
    # Verify customer is associated with this shop
    user_shop = session.exec(
        select(UserShop).where(
            UserShop.user_id == current_user.user_id,
            UserShop.shop_id == appointment_data.shop_id,
            UserShop.is_active
        )
    ).first()
    
    # If not associated, create customer relationship
    if not user_shop:
        user_shop = UserShop(
            user_id=current_user.user_id,
            shop_id=appointment_data.shop_id,
            role="customer"
        )
        session.add(user_shop)
        session.flush()
    
    # Create appointment
    appointment = Appointment(
        **appointment_data.model_dump(),
        customer_id=current_user.user_id
    )
    session.add(appointment)
    session.commit()
    session.refresh(appointment)
    
    return appointment


@router.get("/my-appointments", response_model=List[AppointmentRead])
def get_my_appointments(
    status: Optional[AppointmentStatus] = None,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get all appointments for logged-in customer."""
    query = select(Appointment).where(
        Appointment.customer_id == current_user.user_id
    )
    
    if status:
        query = query.where(Appointment.status == status)
    
    query = query.order_by(Appointment.appointment_date.desc())
    return session.exec(query).all()


@router.get("/my-appointments/{appointment_id}")
def get_appointment_details(
    appointment_id: int,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get specific appointment details."""
    appointment = session.exec(
        select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.customer_id == current_user.user_id
        )
    ).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    return appointment


@router.put("/my-appointments/{appointment_id}/cancel")
def cancel_appointment(
    appointment_id: int,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Cancel an appointment (only if not completed)."""
    appointment = session.exec(
        select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.customer_id == current_user.user_id
        )
    ).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    if appointment.status == AppointmentStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel completed appointment"
        )
    
    appointment.status = AppointmentStatus.CANCELLED
    session.commit()
    
    # Notify shop members about cancellation
    from app.services.notification_service import NotificationService
    from app.models.notification import NotificationType
    notification_service = NotificationService(session)
    
    # Get customer info
    customer = session.get(User, current_user.user_id)
    customer_name = customer.full_name if customer else "A customer"
    
    # Notify shop members
    
    members = session.exec(
        select(UserShop).where(
            UserShop.shop_id == appointment.shop_id,
            UserShop.is_active
        )
    ).all()
    
    for member in members:
        notification_service.create_notification(
            user_id=member.user_id,
            type=NotificationType.BOOKING_CANCELLED,
            title="❌ Booking Cancelled",
            message=f"{customer_name} cancelled their appointment on {appointment.appointment_date.strftime('%Y-%m-%d %H:%M')}",
            appointment_id=appointment.id
        )
    
    return {"message": "Appointment cancelled successfully"}


# ==================== SERVICE HISTORY (Login required) ====================

@router.get("/my-service-history")
def get_my_service_history(
    shop_id: Optional[int] = None,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get service history for logged-in customer."""
    query = select(ServiceHistory).where(
        ServiceHistory.customer_id == current_user.user_id
    )
    
    if shop_id:
        query = query.where(ServiceHistory.shop_id == shop_id)
    
    query = query.order_by(ServiceHistory.completed_date.desc())
    history = session.exec(query).all()
    
    return history


# ==================== SHOP OWNER APPOINTMENT MANAGEMENT ====================

@router.get("/shops/{shop_id}/appointments")
def get_shop_appointments(
    shop_id: int,
    status: Optional[AppointmentStatus] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get all appointments for a shop (Owner/Mechanic only)."""
    from app.services.shop_service import ShopService
    
    shop_service = ShopService(session)
    
    # Check if user is owner or mechanic
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop members can view appointments"
        )
    
    query = select(Appointment).where(Appointment.shop_id == shop_id)
    
    if status:
        query = query.where(Appointment.status == status)
    
    if date_from:
        query = query.where(Appointment.appointment_date >= date_from)
    
    if date_to:
        query = query.where(Appointment.appointment_date <= date_to)
    
    query = query.order_by(Appointment.appointment_date.desc())
    appointments = session.exec(query).all()
    
    return appointments


@router.put("/shops/{shop_id}/appointments/{appointment_id}/status")
def update_appointment_status(
    shop_id: int,
    appointment_id: int,
    new_status: AppointmentStatus,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Update appointment status (Owner/Mechanic only)."""
    from app.services.shop_service import ShopService
    
    shop_service = ShopService(session)
    
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop members can update appointments"
        )
    
    appointment = session.exec(
        select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.shop_id == shop_id
        )
    ).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    appointment.status = new_status
    session.commit()
    session.refresh(appointment)
    
    # If completed, add to service history
    if new_status == AppointmentStatus.COMPLETED:
        # Get service details
        from app.models.product import Service
        service = session.get(Service, appointment.service_id)
        
        if service:
            history = ServiceHistory(
                shop_id=shop_id,
                customer_id=appointment.customer_id,
                appointment_id=appointment.id,
                service_name=service.name,
                service_description=service.description,
                price=service.price,
                completed_date=datetime.utcnow()
            )
            session.add(history)
            session.commit()
    
    return appointment
