"""Mechanic booking management endpoints - for mechanics to view and accept/reject bookings."""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select, SQLModel

from app.db import get_session
from app.models.appointment import Appointment, AppointmentStatus
from app.models.notification import BookingActionRequest, BookingActionResponse, NotificationStatus
from app.models.user import User
from app.core.security import get_current_user, TokenData
from app.services.shop_service import ShopService
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/mechanic", tags=["mechanic-bookings"])


@router.get("/shops/{shop_id}/pending-bookings")
def get_pending_bookings(
    shop_id: int,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get all pending bookings for mechanics to review (Owner/Mechanic only)."""
    shop_service = ShopService(session)
    
    # Check if user is shop member
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop members can view bookings"
        )
    
    # Get pending appointments
    appointments = session.exec(
        select(Appointment).where(
            Appointment.shop_id == shop_id,
            Appointment.status == AppointmentStatus.PENDING
        ).order_by(Appointment.appointment_date.asc())
    ).all()
    
    # Enrich with customer info
    result = []
    for appt in appointments:
        customer = session.get(User, appt.customer_id)
        result.append({
            "appointment_id": appt.id,
            "customer": {
                "id": appt.customer_id,
                "name": customer.full_name if customer else "Unknown",
                "phone": customer.username if customer else None  # Assuming username is phone
            },
            "vehicle_info": appt.vehicle_info,
            "appointment_date": appt.appointment_date,
            "created_at": appt.created_at,
            "service_price": appt.service_price,
            "mobile_service_fee": appt.mobile_service_fee,
            "total_amount": appt.total_amount,
            "notes": appt.notes
        })
    
    return {
        "count": len(result),
        "bookings": result
    }


@router.get("/shops/{shop_id}/bookings/{appointment_id}")
def get_booking_details(
    shop_id: int,
    appointment_id: int,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get detailed booking info for mechanic review."""
    shop_service = ShopService(session)
    
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop members can view bookings"
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
            detail="Booking not found"
        )
    
    # Get customer info
    customer = session.get(User, appointment.customer_id)
    
    # Get service info
    from app.models.product import Service
    service = session.get(Service, appointment.service_id)
    
    return {
        "appointment_id": appointment.id,
        "status": appointment.status,
        "customer": {
            "id": appointment.customer_id,
            "name": customer.full_name if customer else "Unknown",
            "phone": customer.username if customer else None
        },
        "service": {
            "id": service.id if service else None,
            "name": service.name if service else "Unknown",
            "price": appointment.service_price
        },
        "vehicle_info": appointment.vehicle_info,
        "appointment_date": appointment.appointment_date,
        "pricing": {
            "service_price": appointment.service_price,
            "mobile_service_fee": appointment.mobile_service_fee,
            "discount": appointment.discount_amount,
            "tax": appointment.tax_amount,
            "total": appointment.total_amount
        },
        "notes": appointment.notes,
        "created_at": appointment.created_at
    }


@router.post("/shops/{shop_id}/bookings/{appointment_id}/action")
def handle_booking_action(
    shop_id: int,
    appointment_id: int,
    action_request: BookingActionRequest,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Mechanic accepts or rejects a booking."""
    shop_service = ShopService(session)
    notification_service = NotificationService(session)
    
    # Check if user is shop member
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop members can manage bookings"
        )
    
    # Get appointment
    appointment = session.exec(
        select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.shop_id == shop_id
        )
    ).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Check if already processed
    if appointment.status != AppointmentStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Booking already {appointment.status}"
        )
    
    # Get mechanic info
    mechanic = session.get(User, current_user.user_id)
    mechanic_name = mechanic.full_name if mechanic else "Mechanic"
    
    # Handle action
    if action_request.action == "accept":
        # Accept booking
        appointment.status = AppointmentStatus.CONFIRMED
        appointment.updated_at = datetime.utcnow()
        
        # Add mechanic notes
        if action_request.notes:
            appointment.notes = f"{appointment.notes or ''}\n[Mechanic]: {action_request.notes}".strip()
        
        session.commit()
        
        # Notify customer
        notification_service.notify_customer_booking_confirmed(
            appointment=appointment,
            mechanic_name=mechanic_name
        )
        
        return BookingActionResponse(
            success=True,
            message="Booking accepted successfully",
            appointment_id=appointment.id,
            new_status="confirmed",
            customer_notified=True
        )
    
    elif action_request.action == "reject":
        # Reject booking
        appointment.status = AppointmentStatus.CANCELLED
        appointment.updated_at = datetime.utcnow()
        session.commit()
        
        # Notify customer
        notification_service.notify_customer_booking_rejected(
            appointment=appointment,
            reason=action_request.reason
        )
        
        return BookingActionResponse(
            success=True,
            message="Booking rejected",
            appointment_id=appointment.id,
            new_status="cancelled",
            customer_notified=True
        )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action"
        )


@router.get("/my-notifications")
def get_my_notifications(
    status: Optional[str] = Query(None, description="Filter by status: unread, read"),
    limit: int = Query(50, le=100),
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get notifications for current user (mechanic or customer)."""
    from app.models.notification import Notification
    
    query = select(Notification).where(
        Notification.user_id == current_user.user_id
    ).order_by(Notification.created_at.desc())
    
    if status:
        query = query.where(Notification.status == status)
    
    notifications = session.exec(query.limit(limit)).all()
    
    from sqlalchemy import func
    unread_count = session.exec(
        select(func.count(Notification.id)).where(
            Notification.user_id == current_user.user_id,
            Notification.status == NotificationStatus.UNREAD
        )
    ).one()
    
    return {
        "unread_count": unread_count,
        "notifications": [
            {
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "message": n.message,
                "status": n.status,
                "appointment_id": n.appointment_id,
                "created_at": n.created_at,
                "read_at": n.read_at
            }
            for n in notifications
        ]
    }


@router.put("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Mark notification as read."""
    notification_service = NotificationService(session)
    
    notification = notification_service.mark_as_read(
        notification_id=notification_id,
        user_id=current_user.user_id
    )
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    return {"message": "Notification marked as read"}


# ==================== PRODUCT ORDER MANAGEMENT ====================

@router.get("/shops/{shop_id}/pending-orders")
def get_pending_product_orders(
    shop_id: int,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get all pending product orders for shop to review."""
    from app.models.product_order import ProductOrder, OrderStatus
    from app.models.product_order import ProductOrderItem
    
    shop_service = ShopService(session)
    
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop members can view orders"
        )
    
    # Get pending orders
    orders = session.exec(
        select(ProductOrder).where(
            ProductOrder.shop_id == shop_id,
            ProductOrder.status == OrderStatus.PENDING
        ).order_by(ProductOrder.created_at.desc())
    ).all()
    
    # Enrich with customer and items info
    result = []
    for order in orders:
        customer = session.get(User, order.customer_id)
        
        # Get order items
        items = session.exec(
            select(ProductOrderItem).where(ProductOrderItem.order_id == order.id)
        ).all()
        
        result.append({
            "order_id": order.id,
            "customer": {
                "id": order.customer_id,
                "name": customer.full_name if customer else "Unknown",
                "phone": customer.username if customer else None
            },
            "total_amount": order.total_amount,
            "pickup_date": order.pickup_date,
            "created_at": order.created_at,
            "items_count": len(items),
            "notes": order.notes
        })
    
    return {
        "count": len(result),
        "orders": result
    }


class ProductOrderActionRequest(SQLModel):
    """Request model for shop to accept/reject product order."""
    action: str  # "accept" or "reject"
    reason: Optional[str] = None
    estimated_ready_date: Optional[datetime] = None


@router.post("/shops/{shop_id}/orders/{order_id}/action")
def handle_product_order_action(
    shop_id: int,
    order_id: int,
    action_request: ProductOrderActionRequest,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Shop accepts or rejects a product order."""
    from app.models.product_order import ProductOrder, OrderStatus
    
    shop_service = ShopService(session)
    notification_service = NotificationService(session)
    
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop members can manage orders"
        )
    
    # Get order
    order = session.exec(
        select(ProductOrder).where(
            ProductOrder.id == order_id,
            ProductOrder.shop_id == shop_id
        )
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if already processed
    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order already {order.status}"
        )
    
    # Handle action
    if action_request.action == "accept":
        order.status = OrderStatus.CONFIRMED
        order.updated_at = datetime.utcnow()
        session.commit()
        
        # Notify customer
        notification_service.notify_customer_order_confirmed(order)
        
        return {
            "success": True,
            "message": "Order accepted successfully",
            "order_id": order.id,
            "new_status": "confirmed",
            "customer_notified": True
        }
    
    elif action_request.action == "reject":
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.utcnow()
        session.commit()
        
        # Restore stock
        from app.models.product_order import ProductOrderItem
        from app.models.product import Product
        
        items = session.exec(
            select(ProductOrderItem).where(ProductOrderItem.order_id == order.id)
        ).all()
        
        for item in items:
            product = session.get(Product, item.product_id)
            if product:
                product.stock_quantity += item.quantity
        
        session.commit()
        
        # Notify customer
        notification_service.notify_customer_order_rejected(order, action_request.reason)
        
        return {
            "success": True,
            "message": "Order rejected",
            "order_id": order.id,
            "new_status": "cancelled",
            "customer_notified": True
        }
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action"
        )


@router.put("/shops/{shop_id}/orders/{order_id}/ready")
def mark_order_ready(
    shop_id: int,
    order_id: int,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Mark product order as ready for pickup."""
    from app.models.product_order import ProductOrder, OrderStatus
    
    shop_service = ShopService(session)
    notification_service = NotificationService(session)
    
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop members can manage orders"
        )
    
    order = session.exec(
        select(ProductOrder).where(
            ProductOrder.id == order_id,
            ProductOrder.shop_id == shop_id
        )
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    if order.status != OrderStatus.CONFIRMED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must be confirmed before marking ready"
        )
    
    order.status = OrderStatus.READY
    order.updated_at = datetime.utcnow()
    session.commit()
    
    # Notify customer
    notification_service.notify_customer_order_ready(order)
    
    return {
        "message": "Order marked as ready for pickup",
        "order_id": order.id,
        "customer_notified": True
    }


# ==================== TODAY'S BOOKINGS ====================

@router.get("/shops/{shop_id}/today-bookings")
def get_today_bookings(
    shop_id: int,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get today's confirmed bookings for mechanics."""
    shop_service = ShopService(session)
    
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop members can view bookings"
        )
    
    from datetime import date, timedelta
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = today_start + timedelta(days=1)
    
    appointments = session.exec(
        select(Appointment).where(
            Appointment.shop_id == shop_id,
            Appointment.status == AppointmentStatus.CONFIRMED,
            Appointment.appointment_date >= today_start,
            Appointment.appointment_date < today_end
        ).order_by(Appointment.appointment_date.asc())
    ).all()
    
    result = []
    for appt in appointments:
        customer = session.get(User, appt.customer_id)
        result.append({
            "appointment_id": appt.id,
            "customer_name": customer.full_name if customer else "Unknown",
            "vehicle_info": appt.vehicle_info,
            "appointment_time": appt.appointment_date.strftime("%H:%M"),
            "total_amount": appt.total_amount
        })
    
    return {
        "date": date.today().isoformat(),
        "count": len(result),
        "bookings": result
    }
