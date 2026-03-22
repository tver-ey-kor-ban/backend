"""Admin endpoints for platform management."""
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select, func
from sqlalchemy import desc

from app.db import get_session
from app.core.security import require_admin, TokenData
from app.models.user import User
from app.models.shop import Shop, UserShop
from app.models.product import Product, Service
from app.models.appointment import Appointment, AppointmentStatus
from app.models.product_order import ProductOrder, OrderStatus
from app.models.ratings import ProductRating, ServiceRating

router = APIRouter(prefix="/admin", tags=["admin"])


# ==================== USER MANAGEMENT ====================

@router.get("/users", response_model=dict)
def list_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_superuser: Optional[bool] = None,
    current_user: TokenData = Depends(require_admin),
    session: Session = Depends(get_session)
):
    """List all users with filtering options. Admin only."""
    query = select(User)
    
    # Apply filters
    if search:
        query = query.where(
            (User.username.contains(search)) |
            (User.email.contains(search)) |
            (User.full_name.contains(search))
        )
    
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    
    if is_superuser is not None:
        query = query.where(User.is_superuser == is_superuser)
    
    # Get total count
    total_count = session.exec(
        select(func.count(User.id))
    ).one()
    
    # Get paginated results
    query = query.offset(skip).limit(limit).order_by(desc(User.created_at))
    users = session.exec(query).all()
    
    return {
        "total": total_count,
        "skip": skip,
        "limit": limit,
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "full_name": u.full_name,
                "is_active": u.is_active,
                "is_superuser": u.is_superuser,
                "roles": u.roles,
                "created_at": u.created_at.isoformat() if u.created_at else None
            }
            for u in users
        ]
    }


@router.get("/users/{user_id}", response_model=dict)
def get_user_details(
    user_id: int,
    current_user: TokenData = Depends(require_admin),
    session: Session = Depends(get_session)
):
    """Get detailed information about a specific user. Admin only."""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get user's shop memberships
    memberships = session.exec(
        select(UserShop).where(UserShop.user_id == user_id)
    ).all()
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "roles": user.roles,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "shop_memberships": [
            {
                "shop_id": m.shop_id,
                "shop_name": m.shop.name if m.shop else None,
                "role": m.role,
                "is_active": m.is_active
            }
            for m in memberships
        ]
    }


@router.put("/users/{user_id}/status")
def update_user_status(
    user_id: int,
    is_active: bool,
    current_user: TokenData = Depends(require_admin),
    session: Session = Depends(get_session)
):
    """Activate or deactivate a user account. Admin only."""
    # Prevent admin from deactivating themselves
    if user_id == current_user.user_id and not is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = is_active
    session.commit()
    session.refresh(user)
    
    return {
        "message": f"User {'activated' if is_active else 'deactivated'} successfully",
        "user_id": user_id,
        "is_active": is_active
    }


@router.put("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    is_superuser: bool,
    current_user: TokenData = Depends(require_admin),
    session: Session = Depends(get_session)
):
    """Grant or revoke admin privileges. Admin only."""
    # Prevent admin from removing their own admin rights
    if user_id == current_user.user_id and not is_superuser:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove your own admin privileges"
        )
    
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_superuser = is_superuser
    session.commit()
    session.refresh(user)
    
    return {
        "message": f"User {'granted' if is_superuser else 'revoked'} admin privileges",
        "user_id": user_id,
        "is_superuser": is_superuser
    }


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    current_user: TokenData = Depends(require_admin),
    session: Session = Depends(get_session)
):
    """Permanently delete a user account. Admin only."""
    # Prevent admin from deleting themselves
    if user_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    session.delete(user)
    session.commit()
    
    return {
        "message": "User deleted successfully",
        "user_id": user_id
    }


# ==================== SHOP MANAGEMENT ====================

@router.get("/shops", response_model=dict)
def list_all_shops(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = None,
    current_user: TokenData = Depends(require_admin),
    session: Session = Depends(get_session)
):
    """List all shops with filtering options. Admin only."""
    query = select(Shop)
    
    if is_active is not None:
        query = query.where(Shop.is_active == is_active)
    
    # Get total count
    total_count = session.exec(
        select(func.count(Shop.id))
    ).one()
    
    # Get paginated results
    query = query.offset(skip).limit(limit).order_by(desc(Shop.created_at))
    shops = session.exec(query).all()
    
    return {
        "total": total_count,
        "skip": skip,
        "limit": limit,
        "shops": [
            {
                "id": s.id,
                "name": s.name,
                "address": s.address,
                "owner_id": s.owner_id,
                "is_active": s.is_active,
                "created_at": s.created_at.isoformat() if s.created_at else None
            }
            for s in shops
        ]
    }


@router.get("/shops/{shop_id}", response_model=dict)
def get_shop_details(
    shop_id: int,
    current_user: TokenData = Depends(require_admin),
    session: Session = Depends(get_session)
):
    """Get detailed information about a specific shop. Admin only."""
    shop = session.get(Shop, shop_id)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found"
        )
    
    # Get shop statistics
    product_count = session.exec(
        select(func.count(Product.id)).where(Product.shop_id == shop_id)
    ).one()
    
    service_count = session.exec(
        select(func.count(Service.id)).where(Service.shop_id == shop_id)
    ).one()
    
    appointment_count = session.exec(
        select(func.count(Appointment.id)).where(Appointment.shop_id == shop_id)
    ).one()
    
    order_count = session.exec(
        select(func.count(ProductOrder.id)).where(ProductOrder.shop_id == shop_id)
    ).one()
    
    # Get members
    members = session.exec(
        select(UserShop).where(UserShop.shop_id == shop_id)
    ).all()
    
    # Get owner
    owner = next((m for m in members if m.role == "owner"), None)
    
    return {
        "id": shop.id,
        "name": shop.name,
        "description": shop.description,
        "address": shop.address,
        "phone": shop.phone,
        "email": shop.email,
        "owner_id": owner.user_id if owner else None,
        "is_active": shop.is_active,
        "created_at": shop.created_at.isoformat() if shop.created_at else None,
        "statistics": {
            "products": product_count,
            "services": service_count,
            "appointments": appointment_count,
            "orders": order_count
        },
        "members": [
            {
                "user_id": m.user_id,
                "username": m.user.username if m.user else None,
                "role": m.role,
                "is_active": m.is_active
            }
            for m in members
        ]
    }


@router.delete("/shops/{shop_id}")
def admin_delete_shop(
    shop_id: int,
    current_user: TokenData = Depends(require_admin),
    session: Session = Depends(get_session)
):
    """Permanently delete a shop. Admin only."""
    shop = session.get(Shop, shop_id)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found"
        )
    
    session.delete(shop)
    session.commit()
    
    return {
        "message": "Shop deleted successfully",
        "shop_id": shop_id
    }


# ==================== PLATFORM STATISTICS ====================

@router.get("/statistics", response_model=dict)
def get_platform_statistics(
    current_user: TokenData = Depends(require_admin),
    session: Session = Depends(get_session)
):
    """Get platform-wide statistics. Admin only."""
    # User statistics
    total_users = session.exec(select(func.count(User.id))).one()
    active_users = session.exec(
        select(func.count(User.id)).where(User.is_active)
    ).one()
    admin_users = session.exec(
        select(func.count(User.id)).where(User.is_superuser)
    ).one()
    
    # Shop statistics
    total_shops = session.exec(select(func.count(Shop.id))).one()
    active_shops = session.exec(
        select(func.count(Shop.id)).where(Shop.is_active)
    ).one()
    
    # Product/Service statistics
    total_products = session.exec(select(func.count(Product.id))).one()
    total_services = session.exec(select(func.count(Service.id))).one()
    
    # Booking statistics
    total_appointments = session.exec(select(func.count(Appointment.id))).one()
    pending_appointments = session.exec(
        select(func.count(Appointment.id))
        .where(Appointment.status == AppointmentStatus.PENDING)
    ).one()
    completed_appointments = session.exec(
        select(func.count(Appointment.id))
        .where(Appointment.status == AppointmentStatus.COMPLETED)
    ).one()
    
    # Order statistics
    total_orders = session.exec(select(func.count(ProductOrder.id))).one()
    pending_orders = session.exec(
        select(func.count(ProductOrder.id))
        .where(ProductOrder.status == OrderStatus.PENDING)
    ).one()
    completed_orders = session.exec(
        select(func.count(ProductOrder.id))
        .where(ProductOrder.status == OrderStatus.COMPLETED)
    ).one()
    
    # Revenue calculation
    total_appointment_revenue = session.exec(
        select(func.sum(Appointment.total_amount))
        .where(Appointment.status == AppointmentStatus.COMPLETED)
    ).one() or 0
    
    total_order_revenue = session.exec(
        select(func.sum(ProductOrder.total_amount))
        .where(ProductOrder.status == OrderStatus.COMPLETED)
    ).one() or 0
    
    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "inactive": total_users - active_users,
            "admins": admin_users
        },
        "shops": {
            "total": total_shops,
            "active": active_shops,
            "inactive": total_shops - active_shops
        },
        "catalog": {
            "products": total_products,
            "services": total_services
        },
        "appointments": {
            "total": total_appointments,
            "pending": pending_appointments,
            "completed": completed_appointments,
            "cancelled": total_appointments - pending_appointments - completed_appointments
        },
        "orders": {
            "total": total_orders,
            "pending": pending_orders,
            "completed": completed_orders,
            "cancelled": total_orders - pending_orders - completed_orders
        },
        "revenue": {
            "appointments": float(total_appointment_revenue),
            "orders": float(total_order_revenue),
            "total": float(total_appointment_revenue + total_order_revenue)
        }
    }


@router.get("/statistics/daily", response_model=dict)
def get_daily_statistics(
    days: int = Query(30, ge=1, le=365),
    current_user: TokenData = Depends(require_admin),
    session: Session = Depends(get_session)
):
    """Get daily statistics for the last N days. Admin only."""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # This is a simplified version - in production you'd want proper date grouping
    new_users = session.exec(
        select(func.count(User.id))
        .where(User.created_at >= start_date)
    ).one()
    
    new_shops = session.exec(
        select(func.count(Shop.id))
        .where(Shop.created_at >= start_date)
    ).one()
    
    new_appointments = session.exec(
        select(func.count(Appointment.id))
        .where(Appointment.created_at >= start_date)
    ).one()
    
    new_orders = session.exec(
        select(func.count(ProductOrder.id))
        .where(ProductOrder.created_at >= start_date)
    ).one()
    
    return {
        "period_days": days,
        "start_date": start_date.isoformat(),
        "end_date": datetime.utcnow().isoformat(),
        "new_users": new_users,
        "new_shops": new_shops,
        "new_appointments": new_appointments,
        "new_orders": new_orders
    }


# ==================== BOOKINGS & ORDERS ====================

@router.get("/appointments", response_model=dict)
def list_all_appointments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[AppointmentStatus] = None,
    shop_id: Optional[int] = None,
    current_user: TokenData = Depends(require_admin),
    session: Session = Depends(get_session)
):
    """List all appointments across all shops. Admin only."""
    query = select(Appointment)
    
    if status:
        query = query.where(Appointment.status == status)
    
    if shop_id:
        query = query.where(Appointment.shop_id == shop_id)
    
    # Get total count
    total_count = session.exec(
        select(func.count(Appointment.id))
    ).one()
    
    # Get paginated results
    query = query.offset(skip).limit(limit).order_by(desc(Appointment.created_at))
    appointments = session.exec(query).all()
    
    return {
        "total": total_count,
        "skip": skip,
        "limit": limit,
        "appointments": [
            {
                "id": a.id,
                "shop_id": a.shop_id,
                "customer_id": a.customer_id,
                "service_id": a.service_id,
                "status": a.status.value if a.status else None,
                "appointment_date": a.appointment_date.isoformat() if a.appointment_date else None,
                "total_amount": a.total_amount,
                "created_at": a.created_at.isoformat() if a.created_at else None
            }
            for a in appointments
        ]
    }


@router.get("/orders", response_model=dict)
def list_all_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[OrderStatus] = None,
    shop_id: Optional[int] = None,
    current_user: TokenData = Depends(require_admin),
    session: Session = Depends(get_session)
):
    """List all product orders across all shops. Admin only."""
    query = select(ProductOrder)
    
    if status:
        query = query.where(ProductOrder.status == status)
    
    if shop_id:
        query = query.where(ProductOrder.shop_id == shop_id)
    
    # Get total count
    total_count = session.exec(
        select(func.count(ProductOrder.id))
    ).one()
    
    # Get paginated results
    query = query.offset(skip).limit(limit).order_by(desc(ProductOrder.created_at))
    orders = session.exec(query).all()
    
    return {
        "total": total_count,
        "skip": skip,
        "limit": limit,
        "orders": [
            {
                "id": o.id,
                "shop_id": o.shop_id,
                "customer_id": o.customer_id,
                "status": o.status.value if o.status else None,
                "total_amount": o.total_amount,
                "pickup_date": o.pickup_date.isoformat() if o.pickup_date else None,
                "created_at": o.created_at.isoformat() if o.created_at else None
            }
            for o in orders
        ]
    }


# ==================== RATINGS MODERATION ====================

@router.get("/ratings", response_model=dict)
def list_all_ratings(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: TokenData = Depends(require_admin),
    session: Session = Depends(get_session)
):
    """List all ratings across the platform. Admin only."""
    # Get product ratings
    product_ratings = session.exec(
        select(ProductRating).offset(skip).limit(limit)
    ).all()
    
    # Get service ratings
    service_ratings = session.exec(
        select(ServiceRating).offset(skip).limit(limit)
    ).all()
    
    return {
        "product_ratings": [
            {
                "id": r.id,
                "product_id": r.product_id,
                "customer_id": r.customer_id,
                "rating": r.rating,
                "review": r.review,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in product_ratings
        ],
        "service_ratings": [
            {
                "id": r.id,
                "service_id": r.service_id,
                "customer_id": r.customer_id,
                "rating": r.rating,
                "review": r.review,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in service_ratings
        ]
    }


@router.delete("/ratings/product/{rating_id}")
def delete_product_rating(
    rating_id: int,
    current_user: TokenData = Depends(require_admin),
    session: Session = Depends(get_session)
):
    """Delete a product rating. Admin only."""
    rating = session.get(ProductRating, rating_id)
    if not rating:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rating not found"
        )
    
    session.delete(rating)
    session.commit()
    
    return {"message": "Product rating deleted successfully"}


@router.delete("/ratings/service/{rating_id}")
def delete_service_rating(
    rating_id: int,
    current_user: TokenData = Depends(require_admin),
    session: Session = Depends(get_session)
):
    """Delete a service rating. Admin only."""
    rating = session.get(ServiceRating, rating_id)
    if not rating:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rating not found"
        )
    
    session.delete(rating)
    session.commit()
    
    return {"message": "Service rating deleted successfully"}
