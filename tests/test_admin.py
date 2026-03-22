"""Tests for admin endpoints."""
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.user import User
from app.models.shop import Shop
from app.models.product import Product
from app.models.appointment import Appointment, AppointmentStatus
from app.models.product_order import ProductOrder, OrderStatus


class TestAdminUserManagement:
    """Test admin user management endpoints."""
    
    def test_list_all_users_as_admin(self, client: TestClient, admin_user, admin_auth_headers):
        """Test listing all users as admin."""
        response = client.get("/api/v1/admin/users", headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total" in data
        assert len(data["users"]) >= 1
    
    def test_list_users_with_search(self, client: TestClient, admin_user, admin_auth_headers):
        """Test searching users as admin."""
        response = client.get(
            "/api/v1/admin/users?search=admin",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["users"]) >= 1
    
    def test_get_user_details_as_admin(self, client: TestClient, admin_user, shop_owner, admin_auth_headers):
        """Test getting user details as admin."""
        response = client.get(
            f"/api/v1/admin/users/{shop_owner.id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == shop_owner.id
        assert data["username"] == shop_owner.username
        assert "shop_memberships" in data
    
    def test_get_user_details_not_found(self, client: TestClient, admin_user, admin_auth_headers):
        """Test getting non-existent user details."""
        response = client.get("/api/v1/admin/users/99999", headers=admin_auth_headers)
        assert response.status_code == 404
    
    def test_update_user_status_as_admin(self, client: TestClient, admin_user, shop_owner, admin_auth_headers):
        """Test updating user status as admin."""
        response = client.put(
            f"/api/v1/admin/users/{shop_owner.id}/status?is_active=false",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert not data["is_active"]
        assert "deactivated" in data["message"]
    
    def test_cannot_deactivate_self(self, client: TestClient, admin_user, admin_auth_headers):
        """Test admin cannot deactivate their own account."""
        response = client.put(
            f"/api/v1/admin/users/{admin_user.id}/status?is_active=false",
            headers=admin_auth_headers
        )
        assert response.status_code == 400
    
    def test_update_user_role_as_admin(self, client: TestClient, admin_user, shop_owner, admin_auth_headers):
        """Test granting admin privileges as admin."""
        response = client.put(
            f"/api/v1/admin/users/{shop_owner.id}/role?is_superuser=true",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_superuser"]
    
    def test_cannot_remove_own_admin(self, client: TestClient, admin_user, admin_auth_headers):
        """Test admin cannot remove their own admin privileges."""
        response = client.put(
            f"/api/v1/admin/users/{admin_user.id}/role?is_superuser=false",
            headers=admin_auth_headers
        )
        assert response.status_code == 400
    
    def test_delete_user_as_admin(self, client: TestClient, session: Session, admin_user, admin_auth_headers):
        """Test deleting a user as admin."""
        # Create a user to delete
        from app.core.security import get_password_hash
        user_to_delete = User(
            email="delete_me@example.com",
            username="delete_me",
            hashed_password=get_password_hash("password"),
            is_active=True
        )
        session.add(user_to_delete)
        session.commit()
        session.refresh(user_to_delete)
        
        response = client.delete(
            f"/api/v1/admin/users/{user_to_delete.id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
    
    def test_cannot_delete_self(self, client: TestClient, admin_user, admin_auth_headers):
        """Test admin cannot delete their own account."""
        response = client.delete(
            f"/api/v1/admin/users/{admin_user.id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 400
    
    def test_non_admin_cannot_access_users(self, client: TestClient, shop_owner, owner_auth_headers):
        """Test non-admin cannot access admin endpoints."""
        response = client.get("/api/v1/admin/users", headers=owner_auth_headers)
        assert response.status_code == 403


class TestAdminShopManagement:
    """Test admin shop management endpoints."""
    
    def test_list_all_shops_as_admin(self, client: TestClient, admin_user, admin_auth_headers):
        """Test listing all shops as admin."""
        response = client.get("/api/v1/admin/shops", headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "shops" in data
        assert "total" in data
    
    def test_get_shop_details_as_admin(self, client: TestClient, session: Session, admin_user, shop_owner, admin_auth_headers):
        """Test getting shop details as admin."""
        shop = Shop(name="Admin Test Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        response = client.get(
            f"/api/v1/admin/shops/{shop.id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == shop.id
        assert "statistics" in data
        assert "members" in data
    
    def test_delete_shop_as_admin(self, client: TestClient, session: Session, admin_user, shop_owner, admin_auth_headers):
        """Test deleting a shop as admin."""
        shop = Shop(name="Shop To Delete", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        response = client.delete(
            f"/api/v1/admin/shops/{shop.id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 200


class TestAdminStatistics:
    """Test admin statistics endpoints."""
    
    def test_get_platform_statistics(self, client: TestClient, admin_user, admin_auth_headers):
        """Test getting platform-wide statistics."""
        response = client.get("/api/v1/admin/statistics", headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check all expected sections
        assert "users" in data
        assert "shops" in data
        assert "catalog" in data
        assert "appointments" in data
        assert "orders" in data
        assert "revenue" in data
        
        # Check user stats
        assert "total" in data["users"]
        assert "active" in data["users"]
        assert "admins" in data["users"]
    
    def test_get_daily_statistics(self, client: TestClient, admin_user, admin_auth_headers):
        """Test getting daily statistics."""
        response = client.get("/api/v1/admin/statistics/daily?days=7", headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data["period_days"] == 7
        assert "start_date" in data
        assert "end_date" in data
        assert "new_users" in data
        assert "new_shops" in data


class TestAdminBookingsAndOrders:
    """Test admin bookings and orders endpoints."""
    
    def test_list_all_appointments(self, client: TestClient, session: Session, admin_user, shop_owner, customer_user, admin_auth_headers):
        """Test listing all appointments as admin."""
        # Create a shop and appointment
        shop = Shop(name="Appointment Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        appointment = Appointment(
            shop_id=shop.id,
            customer_id=customer_user.id,
            service_price=50.0,
            status=AppointmentStatus.PENDING,
            appointment_date=datetime.utcnow() + timedelta(days=1)
        )
        session.add(appointment)
        session.commit()
        
        response = client.get("/api/v1/admin/appointments", headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "appointments" in data
        assert "total" in data
    
    def test_list_all_orders(self, client: TestClient, session: Session, admin_user, shop_owner, customer_user, admin_auth_headers):
        """Test listing all orders as admin."""
        # Create a shop and order
        shop = Shop(name="Order Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        order = ProductOrder(
            shop_id=shop.id,
            customer_id=customer_user.id,
            total_amount=100.0,
            status=OrderStatus.PENDING
        )
        session.add(order)
        session.commit()
        
        response = client.get("/api/v1/admin/orders", headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "orders" in data
        assert "total" in data


class TestAdminRatings:
    """Test admin ratings management endpoints."""
    
    def test_list_all_ratings(self, client: TestClient, session: Session, admin_user, shop_owner, customer_user, admin_auth_headers):
        """Test listing all ratings as admin."""
        # Create a shop and product with rating
        shop = Shop(name="Rating Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        product = Product(name="Rated Product", price=20, stock_quantity=10, shop_id=shop.id)
        session.add(product)
        session.commit()
        session.refresh(product)
        
        from app.models.ratings import ProductRating
        rating = ProductRating(
            product_id=product.id,
            customer_id=customer_user.id,
            rating=5,
            review="Great product!"
        )
        session.add(rating)
        session.commit()
        
        response = client.get("/api/v1/admin/ratings", headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "product_ratings" in data
        assert "service_ratings" in data
