"""Notification service for creating and managing alerts."""
from datetime import datetime
from typing import Optional, List
import json
from sqlmodel import Session, select

from app.models.notification import Notification, NotificationType, NotificationStatus
from app.models.appointment import Appointment
from app.models.user import User


class NotificationService:
    """Service for handling notifications."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_notification(
        self,
        user_id: int,
        type: NotificationType,
        title: str,
        message: str,
        appointment_id: Optional[int] = None,
        product_order_id: Optional[int] = None,
        data: Optional[dict] = None
    ) -> Notification:
        """Create a new notification."""
        notification = Notification(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            appointment_id=appointment_id,
            product_order_id=product_order_id,
            data=json.dumps(data) if data else None,
            status=NotificationStatus.UNREAD,
            created_at=datetime.utcnow()
        )
        self.session.add(notification)
        self.session.commit()
        self.session.refresh(notification)
        return notification
    
    def notify_shop_new_booking(self, appointment: Appointment) -> List[Notification]:
        """Notify all shop members (owner + mechanics) about new booking."""
        from app.models.shop import UserShop
        
        # Get shop members
        members = self.session.exec(
            select(UserShop).where(
                UserShop.shop_id == appointment.shop_id,
                UserShop.is_active
            )
        ).all()
        
        notifications = []
        
        # Get customer info
        customer = self.session.get(User, appointment.customer_id)
        customer_name = customer.full_name if customer else "Unknown"
        
        for member in members:
            notification = self.create_notification(
                user_id=member.user_id,
                type=NotificationType.NEW_BOOKING,
                title="🔔 New Booking Received",
                message=f"New appointment from {customer_name} on {appointment.appointment_date.strftime('%Y-%m-%d %H:%M')}",
                appointment_id=appointment.id,
                data={
                    "customer_name": customer_name,
                    "appointment_date": appointment.appointment_date.isoformat(),
                    "vehicle_info": appointment.vehicle_info,
                    "total_amount": appointment.total_amount
                }
            )
            notifications.append(notification)
        
        return notifications
    
    def notify_customer_booking_confirmed(
        self,
        appointment: Appointment,
        mechanic_name: Optional[str] = None
    ) -> Notification:
        """Notify customer that booking is confirmed."""
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
                "shop_id": appointment.shop_id
            }
        )
    
    def notify_shop_new_product_order(self, product_order) -> List[Notification]:
        """Notify all shop members (owner + mechanics) about new product order."""
        from app.models.shop import UserShop
        from app.models.user import User
        
        # Get shop members
        members = self.session.exec(
            select(UserShop).where(
                UserShop.shop_id == product_order.shop_id,
                UserShop.is_active
            )
        ).all()
        
        notifications = []
        
        # Get customer info
        customer = self.session.get(User, product_order.customer_id)
        customer_name = customer.full_name if customer else "Unknown"
        
        for member in members:
            notification = self.create_notification(
                user_id=member.user_id,
                type=NotificationType.NEW_PRODUCT_ORDER,
                title="📦 New Product Order",
                message=f"New order from {customer_name} - Total: ${product_order.total_amount:.2f}",
                product_order_id=product_order.id,
                data={
                    "customer_name": customer_name,
                    "total_amount": product_order.total_amount,
                    "pickup_date": product_order.pickup_date.isoformat() if product_order.pickup_date else None
                }
            )
            notifications.append(notification)
        
        return notifications
    
    def notify_customer_order_confirmed(self, product_order) -> Notification:
        """Notify customer that product order is confirmed."""
        return self.create_notification(
            user_id=product_order.customer_id,
            type=NotificationType.ORDER_CONFIRMED,
            title="✅ Order Confirmed",
            message=f"Your product order has been confirmed! Total: ${product_order.total_amount:.2f}",
            product_order_id=product_order.id,
            data={
                "total_amount": product_order.total_amount,
                "pickup_date": product_order.pickup_date.isoformat() if product_order.pickup_date else None,
                "shop_id": product_order.shop_id
            }
        )
    
    def notify_customer_order_rejected(self, product_order, reason: Optional[str] = None) -> Notification:
        """Notify customer that product order is rejected."""
        message = "Sorry, your product order could not be confirmed."
        if reason:
            message += f" Reason: {reason}"
        
        return self.create_notification(
            user_id=product_order.customer_id,
            type=NotificationType.ORDER_REJECTED,
            title="❌ Order Rejected",
            message=message,
            product_order_id=product_order.id,
            data={
                "reason": reason,
                "shop_id": product_order.shop_id
            }
        )
    
    def notify_customer_order_ready(self, product_order) -> Notification:
        """Notify customer that product order is ready for pickup."""
        return self.create_notification(
            user_id=product_order.customer_id,
            type=NotificationType.ORDER_READY,
            title="🎉 Order Ready for Pickup",
            message="Your order is ready! Please come to pick up your items.",
            product_order_id=product_order.id,
            data={
                "total_amount": product_order.total_amount,
                "shop_id": product_order.shop_id
            }
        )
    
    def notify_customer_booking_rejected(
        self,
        appointment: Appointment,
        reason: Optional[str] = None
    ) -> Notification:
        """Notify customer that booking is rejected."""
        message = "Sorry, your appointment could not be confirmed."
        if reason:
            message += f" Reason: {reason}"
        
        return self.create_notification(
            user_id=appointment.customer_id,
            type=NotificationType.BOOKING_REJECTED,
            title="❌ Booking Rejected",
            message=message,
            appointment_id=appointment.id,
            data={
                "reason": reason,
                "shop_id": appointment.shop_id
            }
        )
    
    def get_user_notifications(
        self,
        user_id: int,
        status: Optional[NotificationStatus] = None,
        limit: int = 50
    ) -> List[Notification]:
        """Get notifications for a user."""
        query = select(Notification).where(
            Notification.user_id == user_id
        ).order_by(Notification.created_at.desc())
        
        if status:
            query = query.where(Notification.status == status)
        
        return self.session.exec(query.limit(limit)).all()
    
    def mark_as_read(self, notification_id: int, user_id: int) -> Optional[Notification]:
        """Mark notification as read."""
        notification = self.session.exec(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id
            )
        ).first()
        
        if notification:
            notification.status = NotificationStatus.READ
            notification.read_at = datetime.utcnow()
            self.session.commit()
            self.session.refresh(notification)
        
        return notification
    
    def get_unread_count(self, user_id: int) -> int:
        """Get count of unread notifications."""
        from sqlalchemy import func
        return self.session.exec(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.status == NotificationStatus.UNREAD
            )
        ).one()
