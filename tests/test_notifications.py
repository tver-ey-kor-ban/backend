"""Tests for notification system."""
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.shop import Shop, UserShop, ShopRole
from app.models.product import Service
from app.models.appointment import Appointment, AppointmentStatus
from app.models.notification import Notification, NotificationType, NotificationStatus


class TestNotifications:
    """Test notification system."""
    
    def test_new_booking_notification(self, client: TestClient, session: Session, shop_owner, mechanic_user, customer_user, customer_auth_headers):
        """Test notification sent when customer books."""
        shop = Shop(name="Notify Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        # Add mechanic to shop
        user_shop = UserShop(user_id=mechanic_user.id, shop_id=shop.id, role=ShopRole.MECHANIC)
        session.add(user_shop)
        session.commit()
        
        service = Service(name="Oil Change", price=50, shop_id=shop.id)
        session.add(service)
        session.commit()
        session.refresh(service)
        
        # Customer books service
        response = client.post(
            "/api/v1/product-orders/unified-booking",
            json={
                "shop_id": shop.id,
                "service_id": service.id,
                "appointment_date": (datetime.utcnow() + timedelta(days=1)).isoformat()
            },
            headers=customer_auth_headers
        )
        assert response.status_code == 201  # Created
        
        # Should have notification for mechanic
        mechanic_notifications = session.exec(
            select(Notification).where(
                Notification.user_id == mechanic_user.id,
                Notification.type == NotificationType.NEW_BOOKING
            )
        ).all()
        assert len(mechanic_notifications) >= 1
    
    def test_mechanic_view_notifications(self, client: TestClient, session: Session, shop_owner, mechanic_user, mechanic_auth_headers):
        """Test mechanic viewing their notifications."""
        shop = Shop(name="Mech Notify Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        # Create UserShop entry for owner
        owner_shop = UserShop(user_id=shop_owner.id, shop_id=shop.id, role=ShopRole.OWNER)
        session.add(owner_shop)
        session.commit()
        
        # Add mechanic to shop
        user_shop = UserShop(user_id=mechanic_user.id, shop_id=shop.id, role=ShopRole.MECHANIC)
        session.add(user_shop)
        session.commit()
        
        # Create notification
        notification = Notification(
            user_id=mechanic_user.id,
            type=NotificationType.NEW_BOOKING,
            title="New Booking",
            message="Test booking received"
        )
        session.add(notification)
        session.commit()
        
        response = client.get(
            "/api/v1/mechanic/my-notifications",
            headers=mechanic_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["unread_count"] >= 1
        assert len(data["notifications"]) >= 1
    
    def test_mark_notification_read(self, client: TestClient, session: Session, mechanic_user, mechanic_auth_headers):
        """Test marking notification as read."""
        # Create notification
        notification = Notification(
            user_id=mechanic_user.id,
            type=NotificationType.NEW_BOOKING,
            title="New Booking",
            message="Test booking",
            status=NotificationStatus.UNREAD
        )
        session.add(notification)
        session.commit()
        session.refresh(notification)
        
        response = client.put(
            f"/api/v1/mechanic/notifications/{notification.id}/read",
            headers=mechanic_auth_headers
        )
        assert response.status_code == 200
        
        # Verify notification is marked read
        session.refresh(notification)
        assert notification.status == NotificationStatus.READ
    
    def test_customer_receives_confirmation_notification(self, client: TestClient, session: Session, shop_owner, mechanic_user, customer_user, mechanic_auth_headers, customer_auth_headers):
        """Test customer receives confirmation when booking accepted."""
        shop = Shop(name="Confirm Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        # Add mechanic
        user_shop = UserShop(user_id=mechanic_user.id, shop_id=shop.id, role=ShopRole.MECHANIC)
        session.add(user_shop)
        session.commit()
        
        # Create appointment
        appointment = Appointment(
            shop_id=shop.id,
            customer_id=customer_user.id,
            appointment_date=datetime.utcnow() + timedelta(days=1),
            status=AppointmentStatus.PENDING,
            service_price=50
        )
        session.add(appointment)
        session.commit()
        session.refresh(appointment)
        
        # Mechanic accepts booking
        response = client.post(
            f"/api/v1/mechanic/shops/{shop.id}/bookings/{appointment.id}/action",
            json={"action": "accept"},
            headers=mechanic_auth_headers
        )
        assert response.status_code == 200
        
        # Check customer received notification
        customer_notifications = session.exec(
            select(Notification).where(
                Notification.user_id == customer_user.id,
                Notification.type == NotificationType.BOOKING_CONFIRMED
            )
        ).all()
        assert len(customer_notifications) >= 1
    
    def test_customer_receives_rejection_notification(self, client: TestClient, session: Session, shop_owner, mechanic_user, customer_user, mechanic_auth_headers, customer_auth_headers):
        """Test customer receives rejection notification."""
        shop = Shop(name="Reject Notify Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        # Add mechanic
        user_shop = UserShop(user_id=mechanic_user.id, shop_id=shop.id, role=ShopRole.MECHANIC)
        session.add(user_shop)
        session.commit()
        
        # Create appointment
        appointment = Appointment(
            shop_id=shop.id,
            customer_id=customer_user.id,
            appointment_date=datetime.utcnow() + timedelta(days=1),
            status=AppointmentStatus.PENDING,
            service_price=50
        )
        session.add(appointment)
        session.commit()
        session.refresh(appointment)
        
        # Mechanic rejects booking
        response = client.post(
            f"/api/v1/mechanic/shops/{shop.id}/bookings/{appointment.id}/action",
            json={"action": "reject", "reason": "Fully booked"},
            headers=mechanic_auth_headers
        )
        assert response.status_code == 200
        
        # Check customer received rejection notification
        customer_notifications = session.exec(
            select(Notification).where(
                Notification.user_id == customer_user.id,
                Notification.type == NotificationType.BOOKING_REJECTED
            )
        ).all()
        assert len(customer_notifications) >= 1
