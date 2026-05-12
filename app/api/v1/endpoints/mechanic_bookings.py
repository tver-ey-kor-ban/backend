"""Mechanic booking management endpoints - for mechanics to view and accept/reject bookings."""
from typing import Optional
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, SQLModel

from app.db import get_session
from app.models.appointment import AppointmentStatus
from app.models.notification import BookingActionRequest, BookingActionResponse, NotificationStatus
from app.core.security import get_current_user, TokenData
from app.repositories.shop_repository import ShopRepository
from app.repositories.user_repository import UserRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.order_repository import OrderRepository
from app.services.shop_service import ShopService
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/mechanic", tags=["mechanic-bookings"])


def get_shop_service(session: Session = Depends(get_session)) -> ShopService:
    return ShopService(ShopRepository(session))


def get_notification_service(session: Session = Depends(get_session)) -> NotificationService:
    return NotificationService(
        NotificationRepository(session),
        ShopRepository(session),
        UserRepository(session),
    )


def get_user_repo(session: Session = Depends(get_session)) -> UserRepository:
    return UserRepository(session)


def get_order_repo(session: Session = Depends(get_session)) -> OrderRepository:
    return OrderRepository(session)


def get_product_repo(session: Session = Depends(get_session)) -> ProductRepository:
    return ProductRepository(session)


@router.get("/shops/{shop_id}/pending-bookings")
def get_pending_bookings(
    shop_id: int,
    current_user: TokenData = Depends(get_current_user),
    shop_service: ShopService = Depends(get_shop_service),
    user_repo: UserRepository = Depends(get_user_repo),
    order_repo: OrderRepository = Depends(get_order_repo),
):
    """Get all pending bookings for mechanics to review (Owner/Mechanic only)."""
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only shop members can view bookings")

    appointments = order_repo.get_appointments_by_shop_and_status(shop_id, AppointmentStatus.PENDING)

    result = []
    for appt in appointments:
        customer = user_repo.get_by_id(appt.customer_id)
        result.append({
            "appointment_id": appt.id,
            "customer": {
                "id": appt.customer_id,
                "name": customer.full_name if customer else "Unknown",
                "phone": customer.username if customer else None,
            },
            "vehicle_info": appt.vehicle_info,
            "appointment_date": appt.appointment_date,
            "created_at": appt.created_at,
            "service_price": appt.service_price,
            "mobile_service_fee": appt.mobile_service_fee,
            "total_amount": appt.total_amount,
            "notes": appt.notes,
        })

    return {"count": len(result), "bookings": result}


@router.get("/shops/{shop_id}/bookings/{appointment_id}")
def get_booking_details(
    shop_id: int,
    appointment_id: int,
    current_user: TokenData = Depends(get_current_user),
    shop_service: ShopService = Depends(get_shop_service),
    user_repo: UserRepository = Depends(get_user_repo),
    order_repo: OrderRepository = Depends(get_order_repo),
    product_repo: ProductRepository = Depends(get_product_repo),
):
    """Get detailed booking info for mechanic review."""
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only shop members can view bookings")

    appointment = order_repo.get_appointment_by_id_and_shop(appointment_id, shop_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    customer = user_repo.get_by_id(appointment.customer_id)
    service = product_repo.get_service(appointment.service_id) if appointment.service_id else None

    return {
        "appointment_id": appointment.id,
        "status": appointment.status,
        "customer": {
            "id": appointment.customer_id,
            "name": customer.full_name if customer else "Unknown",
            "phone": customer.username if customer else None,
        },
        "service": {
            "id": service.id if service else None,
            "name": service.name if service else "Unknown",
            "price": appointment.service_price,
        },
        "vehicle_info": appointment.vehicle_info,
        "appointment_date": appointment.appointment_date,
        "pricing": {
            "service_price": appointment.service_price,
            "mobile_service_fee": appointment.mobile_service_fee,
            "discount": appointment.discount_amount,
            "tax": appointment.tax_amount,
            "total": appointment.total_amount,
        },
        "notes": appointment.notes,
        "created_at": appointment.created_at,
    }


@router.post("/shops/{shop_id}/bookings/{appointment_id}/action")
def handle_booking_action(
    shop_id: int,
    appointment_id: int,
    action_request: BookingActionRequest,
    current_user: TokenData = Depends(get_current_user),
    shop_service: ShopService = Depends(get_shop_service),
    notification_service: NotificationService = Depends(get_notification_service),
    user_repo: UserRepository = Depends(get_user_repo),
    order_repo: OrderRepository = Depends(get_order_repo),
):
    """Mechanic accepts or rejects a booking."""
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only shop members can manage bookings")

    appointment = order_repo.get_appointment_by_id_and_shop(appointment_id, shop_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    if appointment.status != AppointmentStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Booking already {appointment.status}")

    mechanic = user_repo.get_by_id(current_user.user_id)
    mechanic_name = mechanic.full_name if mechanic else "Mechanic"

    if action_request.action == "accept":
        appointment.status = AppointmentStatus.CONFIRMED
        appointment.updated_at = datetime.utcnow()
        if action_request.notes:
            appointment.notes = f"{appointment.notes or ''}\n[Mechanic]: {action_request.notes}".strip()
        order_repo.update_appointment(appointment)

        notification_service.notify_customer_booking_confirmed(
            appointment=appointment, mechanic_name=mechanic_name
        )
        return BookingActionResponse(
            success=True,
            message="Booking accepted successfully",
            appointment_id=appointment.id,
            new_status="confirmed",
            customer_notified=True,
        )

    elif action_request.action == "reject":
        appointment.status = AppointmentStatus.CANCELLED
        appointment.updated_at = datetime.utcnow()
        order_repo.update_appointment(appointment)

        notification_service.notify_customer_booking_rejected(
            appointment=appointment, reason=action_request.reason
        )
        return BookingActionResponse(
            success=True,
            message="Booking rejected",
            appointment_id=appointment.id,
            new_status="cancelled",
            customer_notified=True,
        )

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action")


@router.get("/my-notifications")
def get_my_notifications(
    status: Optional[str] = Query(None, description="Filter by status: unread, read"),
    limit: int = Query(50, le=100),
    current_user: TokenData = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """Get notifications for current user (mechanic or customer)."""
    notif_status = NotificationStatus(status) if status else None

    notifications = notification_service.get_user_notifications(
        user_id=current_user.user_id,
        status=notif_status,
        limit=limit,
    )
    unread_count = notification_service.get_unread_count(current_user.user_id)

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
                "read_at": n.read_at,
            }
            for n in notifications
        ],
    }


@router.put("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    current_user: TokenData = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """Mark notification as read."""
    notification = notification_service.mark_as_read(
        notification_id=notification_id,
        user_id=current_user.user_id,
    )
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return {"message": "Notification marked as read"}


# ── Product order management ──────────────────────────────────────────────────

@router.get("/shops/{shop_id}/pending-orders")
def get_pending_product_orders(
    shop_id: int,
    current_user: TokenData = Depends(get_current_user),
    shop_service: ShopService = Depends(get_shop_service),
    user_repo: UserRepository = Depends(get_user_repo),
    order_repo: OrderRepository = Depends(get_order_repo),
):
    """Get all pending product orders for shop to review."""
    from app.models.product_order import OrderStatus

    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only shop members can view orders")

    orders = order_repo.get_orders_by_shop_and_status(shop_id, OrderStatus.PENDING)

    result = []
    for order in orders:
        customer = user_repo.get_by_id(order.customer_id)
        items = order_repo.get_order_items(order.id)
        result.append({
            "order_id": order.id,
            "customer": {
                "id": order.customer_id,
                "name": customer.full_name if customer else "Unknown",
                "phone": customer.username if customer else None,
            },
            "total_amount": order.total_amount,
            "pickup_date": order.pickup_date,
            "created_at": order.created_at,
            "items_count": len(items),
            "notes": order.notes,
        })

    return {"count": len(result), "orders": result}


class ProductOrderActionRequest(SQLModel):
    action: str
    reason: Optional[str] = None
    estimated_ready_date: Optional[datetime] = None


@router.post("/shops/{shop_id}/orders/{order_id}/action")
def handle_product_order_action(
    shop_id: int,
    order_id: int,
    action_request: ProductOrderActionRequest,
    current_user: TokenData = Depends(get_current_user),
    shop_service: ShopService = Depends(get_shop_service),
    notification_service: NotificationService = Depends(get_notification_service),
    order_repo: OrderRepository = Depends(get_order_repo),
):
    """Shop accepts or rejects a product order."""
    from app.models.product_order import OrderStatus

    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only shop members can manage orders")

    order = order_repo.get_order_by_id_and_shop(order_id, shop_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if order.status != OrderStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Order already {order.status}")

    if action_request.action == "accept":
        order.status = OrderStatus.CONFIRMED
        order.updated_at = datetime.utcnow()
        order_repo.update_order(order)
        notification_service.notify_customer_order_confirmed(order)
        return {
            "success": True,
            "message": "Order accepted successfully",
            "order_id": order.id,
            "new_status": "confirmed",
            "customer_notified": True,
        }

    elif action_request.action == "reject":
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.utcnow()
        order_repo.update_order(order)
        order_repo.restore_order_stock(order_id)
        notification_service.notify_customer_order_rejected(order, action_request.reason)
        return {
            "success": True,
            "message": "Order rejected",
            "order_id": order.id,
            "new_status": "cancelled",
            "customer_notified": True,
        }

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action")


@router.put("/shops/{shop_id}/orders/{order_id}/ready")
def mark_order_ready(
    shop_id: int,
    order_id: int,
    current_user: TokenData = Depends(get_current_user),
    shop_service: ShopService = Depends(get_shop_service),
    notification_service: NotificationService = Depends(get_notification_service),
    order_repo: OrderRepository = Depends(get_order_repo),
):
    """Mark product order as ready for pickup."""
    from app.models.product_order import OrderStatus

    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only shop members can manage orders")

    order = order_repo.get_order_by_id_and_shop(order_id, shop_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if order.status != OrderStatus.CONFIRMED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order must be confirmed before marking ready")

    order.status = OrderStatus.READY
    order.updated_at = datetime.utcnow()
    order_repo.update_order(order)
    notification_service.notify_customer_order_ready(order)

    return {"message": "Order marked as ready for pickup", "order_id": order.id, "customer_notified": True}


# ── Today's bookings ──────────────────────────────────────────────────────────

@router.get("/shops/{shop_id}/today-bookings")
def get_today_bookings(
    shop_id: int,
    current_user: TokenData = Depends(get_current_user),
    shop_service: ShopService = Depends(get_shop_service),
    user_repo: UserRepository = Depends(get_user_repo),
    order_repo: OrderRepository = Depends(get_order_repo),
):
    """Get today's confirmed bookings for mechanics."""
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only shop members can view bookings")

    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = today_start + timedelta(days=1)

    appointments = order_repo.get_confirmed_appointments_in_range(shop_id, today_start, today_end)

    result = []
    for appt in appointments:
        customer = user_repo.get_by_id(appt.customer_id)
        result.append({
            "appointment_id": appt.id,
            "customer_name": customer.full_name if customer else "Unknown",
            "vehicle_info": appt.vehicle_info,
            "appointment_time": appt.appointment_date.strftime("%H:%M"),
            "total_amount": appt.total_amount,
        })

    return {"date": date.today().isoformat(), "count": len(result), "bookings": result}
