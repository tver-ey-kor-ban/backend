"""Tests for booking system endpoints."""
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.shop import Shop, UserShop, ShopRole
from app.models.product import Product, Service
from app.models.appointment import Appointment, AppointmentStatus


class TestUnifiedBooking:
    """Test unified booking endpoint."""
    
    def test_book_service_only(self, client: TestClient, session: Session, shop_owner, customer_user, customer_auth_headers):
        """Test booking service only."""
        shop = Shop(name="Booking Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        service = Service(name="Oil Change", price=50, shop_id=shop.id)
        session.add(service)
        session.commit()
        session.refresh(service)
        
        response = client.post(
            "/api/v1/product-orders/unified-booking",
            json={
                "shop_id": shop.id,
                "service_id": service.id,
                "appointment_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                "vehicle_info": "Toyota Camry 2020"
            },
            headers=customer_auth_headers
        )
        assert response.status_code == 201  # Created
        data = response.json()
        assert "appointment" in data
        assert data["appointment"]["service_id"] == service.id
        assert "pricing" in data["appointment"]
    
    def test_book_product_only(self, client: TestClient, session: Session, shop_owner, customer_user, customer_auth_headers):
        """Test ordering products only."""
        shop = Shop(name="Product Order Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        product = Product(name="Oil Filter", price=25, stock_quantity=100, shop_id=shop.id)
        session.add(product)
        session.commit()
        session.refresh(product)
        
        response = client.post(
            "/api/v1/product-orders/unified-booking",
            json={
                "shop_id": shop.id,
                "product_items": [
                    {"product_id": product.id, "quantity": 2}
                ],
                "pickup_date": (datetime.utcnow() + timedelta(days=2)).isoformat()
            },
            headers=customer_auth_headers
        )
        assert response.status_code == 201  # Created
        data = response.json()
        assert "product_order" in data
        assert data["product_order"]["total_amount"] == 50.00
    
    def test_book_service_and_product(self, client: TestClient, session: Session, shop_owner, customer_user, customer_auth_headers):
        """Test combined booking (service + product)."""
        shop = Shop(name="Combined Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        service = Service(name="Oil Change", price=50, shop_id=shop.id)
        product = Product(name="Oil Filter", price=25, stock_quantity=100, shop_id=shop.id)
        session.add(service)
        session.add(product)
        session.commit()
        session.refresh(service)
        session.refresh(product)
        
        response = client.post(
            "/api/v1/product-orders/unified-booking",
            json={
                "shop_id": shop.id,
                "service_id": service.id,
                "product_items": [
                    {"product_id": product.id, "quantity": 1}
                ],
                "appointment_date": (datetime.utcnow() + timedelta(days=1)).isoformat()
            },
            headers=customer_auth_headers
        )
        assert response.status_code == 201  # Created
        data = response.json()
        assert "appointment" in data
        assert "product_order" in data
    
    def test_calculate_price_preview(self, client: TestClient, session: Session, shop_owner, customer_user, customer_auth_headers):
        """Test price calculation preview."""
        shop = Shop(name="Price Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        service = Service(name="Oil Change", price=50, shop_id=shop.id)
        product = Product(name="Oil Filter", price=25, stock_quantity=100, shop_id=shop.id)
        session.add(service)
        session.add(product)
        session.commit()
        session.refresh(service)
        session.refresh(product)
        
        response = client.post(
            "/api/v1/product-orders/calculate-price",
            json={
                "shop_id": shop.id,
                "service_id": service.id,
                "product_items": [
                    {"product_id": product.id, "quantity": 2}
                ]
            },
            headers=customer_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "pricing" in data
        assert data["pricing"]["service_price"] == 50
        assert data["pricing"]["products_subtotal"] == 50
        assert data["pricing"]["total_amount"] == 100


class TestBookingManagement:
    """Test booking management by mechanics."""
    
    def test_mechanic_view_pending_bookings(self, client: TestClient, session: Session, shop_owner, mechanic_user, customer_user, mechanic_auth_headers):
        """Test mechanic viewing pending bookings."""
        shop = Shop(name="Pending Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        # Add mechanic to shop
        user_shop = UserShop(user_id=mechanic_user.id, shop_id=shop.id, role=ShopRole.MECHANIC)
        session.add(user_shop)
        session.commit()
        
        # Create a pending appointment
        appointment = Appointment(
            shop_id=shop.id,
            customer_id=customer_user.id,
            appointment_date=datetime.utcnow() + timedelta(days=1),
            status=AppointmentStatus.PENDING,
            service_price=50
        )
        session.add(appointment)
        session.commit()
        
        response = client.get(
            f"/api/v1/mechanic/shops/{shop.id}/pending-bookings",
            headers=mechanic_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1
    
    def test_mechanic_accept_booking(self, client: TestClient, session: Session, shop_owner, mechanic_user, customer_user, mechanic_auth_headers):
        """Test mechanic accepting a booking."""
        shop = Shop(name="Accept Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        # Add mechanic to shop
        user_shop = UserShop(user_id=mechanic_user.id, shop_id=shop.id, role=ShopRole.MECHANIC)
        session.add(user_shop)
        session.commit()
        
        # Create pending appointment
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
        
        response = client.post(
            f"/api/v1/mechanic/shops/{shop.id}/bookings/{appointment.id}/action",
            json={"action": "accept"},
            headers=mechanic_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["new_status"] == "confirmed"
    
    def test_mechanic_reject_booking(self, client: TestClient, session: Session, shop_owner, mechanic_user, customer_user, mechanic_auth_headers):
        """Test mechanic rejecting a booking."""
        shop = Shop(name="Reject Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        # Add mechanic to shop
        user_shop = UserShop(user_id=mechanic_user.id, shop_id=shop.id, role=ShopRole.MECHANIC)
        session.add(user_shop)
        session.commit()
        
        # Create pending appointment
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
        
        response = client.post(
            f"/api/v1/mechanic/shops/{shop.id}/bookings/{appointment.id}/action",
            json={"action": "reject", "reason": "Fully booked"},
            headers=mechanic_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["new_status"] == "cancelled"


class TestCustomerBookingActions:
    """Test customer booking actions."""
    
    def test_customer_cancel_appointment(self, client: TestClient, session: Session, shop_owner, customer_user, customer_auth_headers):
        """Test customer cancelling their appointment."""
        shop = Shop(name="Cancel Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
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
        
        response = client.put(
            f"/api/v1/customers/my-appointments/{appointment.id}/cancel",
            headers=customer_auth_headers
        )
        assert response.status_code == 200
        assert "cancelled" in response.json()["message"]
    
    def test_customer_view_my_appointments(self, client: TestClient, session: Session, shop_owner, customer_user, customer_auth_headers):
        """Test customer viewing their appointments."""
        shop = Shop(name="My Appointments Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        appointment = Appointment(
            shop_id=shop.id,
            customer_id=customer_user.id,
            appointment_date=datetime.utcnow() + timedelta(days=1),
            status=AppointmentStatus.PENDING,
            service_price=50
        )
        session.add(appointment)
        session.commit()
        
        response = client.get(
            "/api/v1/customers/my-appointments",
            headers=customer_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
