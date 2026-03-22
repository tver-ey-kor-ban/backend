"""Tests for products and services endpoints."""
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.shop import Shop, UserShop, ShopRole
from app.models.product import Product, Service, ServiceType


class TestProductEndpoints:
    """Test product management endpoints."""
    
    def test_create_product_as_owner(self, client: TestClient, session: Session, shop_owner, owner_auth_headers):
        """Test creating product as shop owner."""
        shop = Shop(name="Product Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        # Create UserShop entry for owner
        user_shop = UserShop(user_id=shop_owner.id, shop_id=shop.id, role=ShopRole.OWNER)
        session.add(user_shop)
        session.commit()
        
        response = client.post(
            f"/api/v1/shops/{shop.id}/products",
            json={
                "name": "Oil Filter",
                "description": "High quality oil filter",
                "price": 25.99,
                "stock_quantity": 100,
                "sku": "OF-001"
            },
            headers=owner_auth_headers
        )
        assert response.status_code == 201  # Created
        data = response.json()
        assert data["name"] == "Oil Filter"
        assert data["price"] == 25.99
    
    def test_create_product_as_mechanic(self, client: TestClient, session: Session, shop_owner, mechanic_user, mechanic_auth_headers):
        """Test creating product as mechanic (should fail)."""
        shop = Shop(name="Product Shop 2", address="123 St", owner_id=shop_owner.id)
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
        
        response = client.post(
            f"/api/v1/shops/{shop.id}/products",
            json={"name": "Oil Filter", "price": 25.99},
            headers=mechanic_auth_headers
        )
        assert response.status_code == 403
    
    def test_list_products_as_member(self, client: TestClient, session: Session, shop_owner, owner_auth_headers):
        """Test listing products as shop member."""
        shop = Shop(name="Product Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        # Create UserShop entry for owner
        user_shop = UserShop(user_id=shop_owner.id, shop_id=shop.id, role=ShopRole.OWNER)
        session.add(user_shop)
        session.commit()
        
        product = Product(
            name="Brake Pad",
            price=45.99,
            stock_quantity=50,
            shop_id=shop.id
        )
        session.add(product)
        session.commit()
        
        response = client.get(f"/api/v1/shops/{shop.id}/products", headers=owner_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
    
    def test_update_product_as_owner(self, client: TestClient, session: Session, shop_owner, owner_auth_headers):
        """Test updating product as owner."""
        shop = Shop(name="Update Product Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        # Create UserShop entry for owner
        user_shop = UserShop(user_id=shop_owner.id, shop_id=shop.id, role=ShopRole.OWNER)
        session.add(user_shop)
        session.commit()
        
        product = Product(name="Air Filter", price=15.99, stock_quantity=30, shop_id=shop.id)
        session.add(product)
        session.commit()
        session.refresh(product)
        
        response = client.put(
            f"/api/v1/shops/{shop.id}/products/{product.id}",
            json={
                "name": "Air Filter",
                "price": 19.99,
                "stock_quantity": 30
            },
            headers=owner_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["price"] == 19.99
    
    def test_delete_product_as_owner(self, client: TestClient, session: Session, shop_owner, owner_auth_headers):
        """Test deleting product as owner."""
        shop = Shop(name="Delete Product Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        # Create UserShop entry for owner
        user_shop = UserShop(user_id=shop_owner.id, shop_id=shop.id, role=ShopRole.OWNER)
        session.add(user_shop)
        session.commit()
        
        product = Product(name="Spark Plug", price=8.99, stock_quantity=100, shop_id=shop.id)
        session.add(product)
        session.commit()
        session.refresh(product)
        
        response = client.delete(
            f"/api/v1/shops/{shop.id}/products/{product.id}",
            headers=owner_auth_headers
        )
        assert response.status_code == 200


class TestServiceEndpoints:
    """Test service management endpoints."""
    
    def test_create_service_as_owner(self, client: TestClient, session: Session, shop_owner, owner_auth_headers):
        """Test creating service as shop owner."""
        shop = Shop(name="Service Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        # Create UserShop entry for owner
        user_shop = UserShop(user_id=shop_owner.id, shop_id=shop.id, role=ShopRole.OWNER)
        session.add(user_shop)
        session.commit()
        
        response = client.post(
            f"/api/v1/shops/{shop.id}/services",
            json={
                "name": "Oil Change",
                "description": "Full oil change service",
                "price": 49.99,
                "duration_minutes": 30,
                "service_type": "shop_based"
            },
            headers=owner_auth_headers
        )
        assert response.status_code == 201  # Created
        data = response.json()
        assert data["name"] == "Oil Change"
        assert data["price"] == 49.99
    
    def test_create_mobile_service(self, client: TestClient, session: Session, shop_owner, owner_auth_headers):
        """Test creating mobile service."""
        shop = Shop(name="Mobile Service Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        # Create UserShop entry for owner
        user_shop = UserShop(user_id=shop_owner.id, shop_id=shop.id, role=ShopRole.OWNER)
        session.add(user_shop)
        session.commit()
        
        response = client.post(
            f"/api/v1/shops/{shop.id}/services",
            json={
                "name": "Mobile Tire Change",
                "description": "We come to you",
                "price": 79.99,
                "duration_minutes": 45,
                "service_type": "mobile",
                "mobile_service_area": "Downtown",
                "mobile_service_fee": 25.00
            },
            headers=owner_auth_headers
        )
        assert response.status_code == 201  # Created
        data = response.json()
        assert data["service_type"] == "mobile"
        assert data["mobile_service_fee"] == 25.00
    
    def test_list_services_by_type(self, client: TestClient, session: Session, shop_owner, owner_auth_headers):
        """Test listing services filtered by type."""
        shop = Shop(name="Filter Service Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        # Create UserShop entry for owner
        user_shop = UserShop(user_id=shop_owner.id, shop_id=shop.id, role=ShopRole.OWNER)
        session.add(user_shop)
        session.commit()
        
        # Create shop-based service
        service1 = Service(name="Oil Change", price=50, shop_id=shop.id, service_type=ServiceType.SHOP_BASED)
        session.add(service1)
        
        # Create mobile service
        service2 = Service(name="Mobile Repair", price=100, shop_id=shop.id, service_type=ServiceType.MOBILE)
        session.add(service2)
        session.commit()
        
        # Get only mobile services
        response = client.get(f"/api/v1/shops/{shop.id}/services?service_type=mobile", headers=owner_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Mobile Repair"
    
    def test_list_services_by_type_grouped(self, client: TestClient, session: Session, shop_owner, owner_auth_headers):
        """Test listing services grouped by type."""
        shop = Shop(name="Grouped Service Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        # Create UserShop entry for owner
        owner_shop = UserShop(user_id=shop_owner.id, shop_id=shop.id, role=ShopRole.OWNER)
        session.add(owner_shop)
        session.commit()
        
        # Create services
        service1 = Service(name="Oil Change", price=50, shop_id=shop.id, service_type=ServiceType.SHOP_BASED)
        service2 = Service(name="Mobile Repair", price=100, shop_id=shop.id, service_type=ServiceType.MOBILE)
        session.add(service1)
        session.add(service2)
        session.commit()
        
        response = client.get(
            f"/api/v1/shops/{shop.id}/services/by-type",
            headers=owner_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "shop_based" in data
        assert "mobile" in data
