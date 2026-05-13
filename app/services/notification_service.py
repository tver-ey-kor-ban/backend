"""Notification service for creating and managing alerts."""
from datetime import datetime
from typing import Optional, List
import json

from app.models.notification import Notification, NotificationType, NotificationStatus
from app.models.appointment import Appointment
from app.repositories.notification_repository import NotificationRepository
from app.repositories.shop_repository import ShopRepository
from app.repositories.user_repository import UserRepository


class NotificationService:
    def __init__(
        self,
        notif_repo: NotificationRepository,
        shop_repo: ShopRepository,
        user_repo: UserRepository,
    ):
        self.notif_repo = notif_repo
        self.shop_repo = shop_repo
        self.user_repo = user_repo

    def create_notification(
        self,
        user_id: int,
        type: NotificationType,
        title: str,
        message: str,
        appointment_id: Optional[int] = None,
        product_order_id: Optional[int] = None,
        data: Optional[dict] = None,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            appointment_id=appointment_id,
            product_order_id=product_order_id,
            data=json.dumps(data) if data else None,
            status=NotificationStatus.UNREAD,
            created_at=datetime.utcnow(),
        )
        return self.notif_repo.save(notification)

    def notify_shop_new_booking(self, appointment: Appointment) -> List[Notification]:
        members = self.shop_repo.get_active_members(appointment.shop_id)
        customer = self.user_repo.get_by_id(appointment.customer_id)
        customer_name = customer.full_name if customer else "Unknown"

        return [
            self.create_notification(
                user_id=member.user_id,
                type=NotificationType.NEW_BOOKING,
                title="🔔 New Booking Received",
                message=f"New appointment from {customer_name} on {appointment.appointment_date.strftime('%Y-%m-%d %H:%M')}",
                appointment_id=appointment.id,
                data={
                    "customer_name": customer_name,
                    "appointment_date": appointment.appointment_date.isoformat(),
                    "vehicle_info": appointment.vehicle_info,
                    "total_amount": appointment.total_amount,
                },
            )
            for member in members
        ]

    def notify_customer_booking_confirmed(
        self,
        appointment: Appointment,
        mechanic_name: Optional[str] = None,
    ) -> Notification:
        message = "Your appointment has been confirmed!"
        if mechanic_name:
            message += f" {mechanic_name} will service your vehicle."

        return self.create_notification(
            user_id=appointment.customer_id,
            type=NotificationType.BOOKING_CONFIRMED,
            title="✅ Booking Confirmed",
            message=message,
            appointment_id=appointment.id,
            data={
                "appointment_date": appointment.appointment_date.isoformat(),
                "mechanic_name": mechanic_name,
                "shop_id": appointment.shop_id,
            },
        )

    def notify_customer_booking_rejected(
        self,
        appointment: Appointment,
        reason: Optional[str] = None,
    ) -> Notification:
        message = "Sorry, your appointment could not be confirmed."
        if reason:
            message += f" Reason: {reason}"

        return self.create_notification(
            user_id=appointment.customer_id,
            type=NotificationType.BOOKING_REJECTED,
            title="❌ Booking Rejected",
            message=message,
            appointment_id=appointment.id,
            data={"reason": reason, "shop_id": appointment.shop_id},
        )

    def notify_shop_new_product_order(self, product_order) -> List[Notification]:
        members = self.shop_repo.get_active_members(product_order.shop_id)
        customer = self.user_repo.get_by_id(product_order.customer_id)
        customer_name = customer.full_name if customer else "Unknown"

        return [
            self.create_notification(
                user_id=member.user_id,
                type=NotificationType.NEW_PRODUCT_ORDER,
                title="📦 New Product Order",
                message=f"New order from {customer_name} - Total: ${product_order.total_amount:.2f}",
                product_order_id=product_order.id,
                data={
                    "customer_name": customer_name,
                    "total_amount": product_order.total_amount,
                    "pickup_date": product_order.pickup_date.isoformat() if product_order.pickup_date else None,
                },
            )
            for member in members
        ]

    def notify_customer_order_confirmed(self, product_order) -> Notification:
        return self.create_notification(
            user_id=product_order.customer_id,
            type=NotificationType.ORDER_CONFIRMED,
            title="✅ Order Confirmed",
            message=f"Your product order has been confirmed! Total: ${product_order.total_amount:.2f}",
            product_order_id=product_order.id,
            data={
                "total_amount": product_order.total_amount,
                "pickup_date": product_order.pickup_date.isoformat() if product_order.pickup_date else None,
                "shop_id": product_order.shop_id,
            },
        )

    def notify_customer_order_rejected(self, product_order, reason: Optional[str] = None) -> Notification:
        message = "Sorry, your product order could not be confirmed."
        if reason:
            message += f" Reason: {reason}"

        return self.create_notification(
            user_id=product_order.customer_id,
            type=NotificationType.ORDER_REJECTED,
            title="❌ Order Rejected",
            message=message,
            product_order_id=product_order.id,
            data={"reason": reason, "shop_id": product_order.shop_id},
        )

    def notify_customer_order_ready(self, product_order) -> Notification:
        return self.create_notification(
            user_id=product_order.customer_id,
            type=NotificationType.ORDER_READY,
            title="🎉 Order Ready for Pickup",
            message="Your order is ready! Please come to pick up your items.",
            product_order_id=product_order.id,
            data={
                "total_amount": product_order.total_amount,
                "shop_id": product_order.shop_id,
            },
        )

    def get_user_notifications(
        self,
        user_id: int,
        status: Optional[NotificationStatus] = None,
        limit: int = 50,
    ) -> List[Notification]:
        return self.notif_repo.get_user_notifications(user_id, status, limit)

    def mark_as_read(self, notification_id: int, user_id: int) -> Optional[Notification]:
        notification = self.notif_repo.get_by_id_and_user(notification_id, user_id)
        if not notification:
            return None
        return self.notif_repo.mark_as_read(notification)

    def get_unread_count(self, user_id: int) -> int:
        return self.notif_repo.get_unread_count(user_id)
