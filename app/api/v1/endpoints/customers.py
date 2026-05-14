"""Customer endpoints for browsing, booking appointments, and viewing service history."""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select

from app.db import get_session
from app.models.appointment import Appointment, AppointmentCreate, AppointmentRead, AppointmentStatus, ServiceHistory
from app.models.shop import UserShop
from app.core.security import get_current_user, TokenData
from app.repositories.shop_repository import ShopRepository
from app.repositories.user_repository import UserRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.order_repository import OrderRepository
from app.services.shop_service import ShopService
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/customers", tags=["customers"])


def get_shop_service(session: Session = Depends(get_session)) -> ShopService:
    return ShopService(ShopRepository(session))


def get_notification_service(session: Session = Depends(get_session)) -> NotificationService:
    return NotificationService(
        NotificationRepository(session),
        ShopRepository(session),
        UserRepository(session),
    )


def get_shop_repo(session: Session = Depends(get_session)) -> ShopRepository:
    return ShopRepository(session)


def get_user_repo(session: Session = Depends(get_session)) -> UserRepository:
    return UserRepository(session)


def get_order_repo(session: Session = Depends(get_session)) -> OrderRepository:
    return OrderRepository(session)


# ==================== PUBLIC BROWSING (No login required) ====================

@router.get("/shops/{shop_id}/browse/products")
def browse_products(
    shop_id: int,
    search: Optional[str] = Query(None, description="Search by name or description"),
    q: Optional[str] = Query(None, include_in_schema=False),  # legacy alias
    category_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    """Browse products in a shop (PUBLIC - no login required)."""
    from app.models.product import Product
    from app.models.ratings import ProductRating
    from sqlalchemy import func

    term = search or q
    conditions = [Product.shop_id == shop_id, Product.is_active]
    if category_id:
        conditions.append(Product.category_id == category_id)
    if term:
        conditions.append(
            Product.name.ilike(f"%{term}%") | Product.description.ilike(f"%{term}%")
        )

    total = session.execute(
        select(func.count()).select_from(Product).where(*conditions)
    ).scalar() or 0

    offset = (page - 1) * limit
    stmt = (
        select(
            Product,
            func.coalesce(func.avg(ProductRating.rating), 0.0).label("avg_rating"),
            func.count(ProductRating.id).label("rating_count"),
        )
        .outerjoin(ProductRating, ProductRating.product_id == Product.id)
        .where(*conditions)
        .group_by(Product.id)
        .offset(offset)
        .limit(limit)
    )
    rows = session.execute(stmt).all()

    items = [
        {
            "id": row.Product.id,
            "name": row.Product.name,
            "description": row.Product.description,
            "price": row.Product.price,
            "image_url": row.Product.image_url,
            "thumbnail_url": row.Product.thumbnail_url,
            "is_available": row.Product.is_active and row.Product.stock_quantity > 0,
            "stock_quantity": row.Product.stock_quantity,
            "rating": round(float(row.avg_rating), 1),
            "rating_count": row.rating_count,
        }
        for row in rows
    ]
    return {"items": items, "total": total, "page": page, "limit": limit}


@router.get("/shops/{shop_id}/browse/services")
def browse_services(
    shop_id: int,
    search: Optional[str] = Query(None, description="Search by name or description"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    """Browse services in a shop (PUBLIC - no login required)."""
    from app.models.product import Service
    from app.models.ratings import ServiceRating
    from sqlalchemy import func

    conditions = [Service.shop_id == shop_id, Service.is_active]
    if search:
        conditions.append(
            Service.name.ilike(f"%{search}%") | Service.description.ilike(f"%{search}%")
        )

    total = session.execute(
        select(func.count()).select_from(Service).where(*conditions)
    ).scalar() or 0

    offset = (page - 1) * limit
    stmt = (
        select(
            Service,
            func.coalesce(func.avg(ServiceRating.rating), 0.0).label("avg_rating"),
            func.count(ServiceRating.id).label("rating_count"),
        )
        .outerjoin(ServiceRating, ServiceRating.service_id == Service.id)
        .where(*conditions)
        .group_by(Service.id)
        .offset(offset)
        .limit(limit)
    )
    rows = session.execute(stmt).all()

    items = [
        {
            "id": row.Service.id,
            "name": row.Service.name,
            "description": row.Service.description,
            "price": row.Service.price,
            "estimated_duration_minutes": row.Service.duration_minutes,
            "service_type": row.Service.service_type,
            "image_url": row.Service.image_url,
            "is_available": row.Service.is_active,
            "rating": round(float(row.avg_rating), 1),
            "rating_count": row.rating_count,
        }
        for row in rows
    ]
    return {"items": items, "total": total, "page": page, "limit": limit}


@router.get("/shops/{shop_id}/browse/shop-info")
def browse_shop_info(
    shop_id: int,
    session: Session = Depends(get_session),
):
    """Get public shop information (PUBLIC - no login required)."""
    from app.models.shop import Shop

    shop = session.get(Shop, shop_id)
    if not shop or not shop.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found")

    return {
        "id": shop.id,
        "name": shop.name,
        "description": shop.description,
        "address": shop.address,
        "phone": shop.phone,
        "email": shop.email,
        "is_active": shop.is_active,
        "created_at": shop.created_at,
    }


@router.get("/shops/{shop_id}/browse/products/{product_id}")
def browse_product_detail(
    shop_id: int,
    product_id: int,
    session: Session = Depends(get_session),
):
    """Get a single product detail (PUBLIC - no login required)."""
    from app.models.product import Product
    from app.models.ratings import ProductRating
    from sqlalchemy import func

    stmt = (
        select(
            Product,
            func.coalesce(func.avg(ProductRating.rating), 0.0).label("avg_rating"),
            func.count(ProductRating.id).label("rating_count"),
        )
        .outerjoin(ProductRating, ProductRating.product_id == Product.id)
        .where(Product.id == product_id, Product.shop_id == shop_id, Product.is_active)
        .group_by(Product.id)
    )
    row = session.execute(stmt).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    return {
        "id": row.Product.id,
        "name": row.Product.name,
        "description": row.Product.description,
        "price": row.Product.price,
        "image_url": row.Product.image_url,
        "thumbnail_url": row.Product.thumbnail_url,
        "is_available": row.Product.is_active and row.Product.stock_quantity > 0,
        "stock_quantity": row.Product.stock_quantity,
        "rating": round(float(row.avg_rating), 1),
        "rating_count": row.rating_count,
    }


@router.get("/shops/{shop_id}/browse/services/{service_id}")
def browse_service_detail(
    shop_id: int,
    service_id: int,
    session: Session = Depends(get_session),
):
    """Get a single service detail (PUBLIC - no login required)."""
    from app.models.product import Service
    from app.models.ratings import ServiceRating
    from sqlalchemy import func

    stmt = (
        select(
            Service,
            func.coalesce(func.avg(ServiceRating.rating), 0.0).label("avg_rating"),
            func.count(ServiceRating.id).label("rating_count"),
        )
        .outerjoin(ServiceRating, ServiceRating.service_id == Service.id)
        .where(Service.id == service_id, Service.shop_id == shop_id, Service.is_active)
        .group_by(Service.id)
    )
    row = session.execute(stmt).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

    return {
        "id": row.Service.id,
        "name": row.Service.name,
        "description": row.Service.description,
        "price": row.Service.price,
        "estimated_duration_minutes": row.Service.duration_minutes,
        "service_type": row.Service.service_type,
        "image_url": row.Service.image_url,
        "is_available": row.Service.is_active,
        "rating": round(float(row.avg_rating), 1),
        "rating_count": row.rating_count,
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
    order_repo: OrderRepository = Depends(get_order_repo),
    shop_repo: ShopRepository = Depends(get_shop_repo),
    user_repo: UserRepository = Depends(get_user_repo),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """Cancel an appointment (only if not completed)."""
    from app.models.notification import NotificationType

    appointment = order_repo.get_appointment_by_customer_and_id(appointment_id, current_user.user_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    if appointment.status == AppointmentStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot cancel completed appointment")

    appointment.status = AppointmentStatus.CANCELLED
    order_repo.update_appointment(appointment)

    customer = user_repo.get_by_id(current_user.user_id)
    customer_name = customer.full_name if customer else "A customer"

    for member in shop_repo.get_active_members(appointment.shop_id):
        notification_service.create_notification(
            user_id=member.user_id,
            type=NotificationType.BOOKING_CANCELLED,
            title="❌ Booking Cancelled",
            message=f"{customer_name} cancelled their appointment on {appointment.appointment_date.strftime('%Y-%m-%d %H:%M')}",
            appointment_id=appointment.id,
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
    session: Session = Depends(get_session),
    shop_service: ShopService = Depends(get_shop_service),
):
    """Get all appointments for a shop (Owner/Mechanic only)."""
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
    session: Session = Depends(get_session),
    shop_service: ShopService = Depends(get_shop_service),
):
    """Update appointment status (Owner/Mechanic only)."""
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
