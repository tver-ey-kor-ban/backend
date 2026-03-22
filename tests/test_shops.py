"""Tests for shop management endpoints."""
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.shop import Shop, UserShop, ShopRole


class TestShopEndpoints:
    """Test shop management endpoints."""
    
    def test_create_shop(self, client: TestClient, owner_auth_headers):
        """Test creating a new shop."""
        response = client.post(
            "/api/v1/shops",
            json={
                "name": "Test Garage",
                "description": "A test garage",
                "address": "123 Test St",
                "phone": "1234567890",
                "email": "garage@test.com"
            },
            headers=owner_auth_headers
        )
        assert response.status_code == 201  # Created
        data = response.json()
        assert data["name"] == "Test Garage"
    
    def test_create_shop_without_auth(self, client: TestClient):
        """Test creating shop without authentication."""
        response = client.post(
            "/api/v1/shops",
            json={
                "name": "Test Garage",
                "address": "123 Test St"
            }
        )
        assert response.status_code == 401
    
    def test_list_shops(self, client: TestClient, session: Session, shop_owner, owner_auth_headers):
        """Test listing shops with authentication."""
        # Create a shop first
        shop = Shop(
            name="Public Shop",
            description="Test shop",
            address="123 St",
            owner_id=shop_owner.id
        )
        session.add(shop)
        session.commit()
        
        response = client.get("/api/v1/shops", headers=owner_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(s["name"] == "Public Shop" for s in data)
    
    def test_get_shop_detail(self, client: TestClient, session: Session, shop_owner, owner_auth_headers):
        """Test getting shop details."""
        shop = Shop(
            name="Detail Shop",
            description="Test shop",
            address="123 St",
            owner_id=shop_owner.id
        )
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        response = client.get(f"/api/v1/shops/{shop.id}", headers=owner_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Detail Shop"
    
    def test_update_shop_as_owner(self, client: TestClient, session: Session, shop_owner, owner_auth_headers):
        """Test updating shop as owner."""
        shop = Shop(
            name="Update Shop",
            description="Test shop",
            address="123 St",
            owner_id=shop_owner.id
        )
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        # Create UserShop entry for owner
        user_shop = UserShop(user_id=shop_owner.id, shop_id=shop.id, role=ShopRole.OWNER)
        session.add(user_shop)
        session.commit()
        
        response = client.put(
            f"/api/v1/shops/{shop.id}",
            json={"name": "Updated Shop Name", "address": "123 St"},
            headers=owner_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Shop Name"
    
    def test_update_shop_as_non_owner(self, client: TestClient, session: Session, shop_owner, mechanic_user, mechanic_auth_headers):
        """Test updating shop as non-owner (should fail)."""
        shop = Shop(
            name="Protected Shop",
            description="Test shop",
            address="123 St",
            owner_id=shop_owner.id
        )
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        response = client.put(
            f"/api/v1/shops/{shop.id}",
            json={"name": "Hacked Name"},
            headers=mechanic_auth_headers
        )
        assert response.status_code == 403
    
    def test_delete_shop_as_owner(self, client: TestClient, session: Session, shop_owner, owner_auth_headers):
        """Test deleting shop as owner."""
        shop = Shop(
            name="Delete Shop",
            description="Test shop",
            address="123 St",
            owner_id=shop_owner.id
        )
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        # Create UserShop entry for owner
        user_shop = UserShop(user_id=shop_owner.id, shop_id=shop.id, role=ShopRole.OWNER)
        session.add(user_shop)
        session.commit()
        
        response = client.delete(
            f"/api/v1/shops/{shop.id}",
            headers=owner_auth_headers
        )
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
    
    def test_add_mechanic_to_shop(self, client: TestClient, session: Session, shop_owner, mechanic_user, owner_auth_headers):
        """Test adding mechanic to shop."""
        shop = Shop(
            name="Mechanic Shop",
            description="Test shop",
            address="123 St",
            owner_id=shop_owner.id
        )
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        # Create UserShop entry for owner
        user_shop = UserShop(user_id=shop_owner.id, shop_id=shop.id, role=ShopRole.OWNER)
        session.add(user_shop)
        session.commit()
        
        response = client.post(
            f"/api/v1/shops/{shop.id}/members",
            json={
                "user_id": mechanic_user.id,
                "shop_id": shop.id,
                "role": "mechanic"
            },
            headers=owner_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "user added as mechanic" in data["message"].lower()
    
    def test_remove_mechanic_from_shop(self, client: TestClient, session: Session, shop_owner, mechanic_user, owner_auth_headers):
        """Test removing mechanic from shop."""
        shop = Shop(
            name="Remove Mechanic Shop",
            description="Test shop",
            address="123 St",
            owner_id=shop_owner.id
        )
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        # Create UserShop entry for owner
        owner_shop = UserShop(user_id=shop_owner.id, shop_id=shop.id, role=ShopRole.OWNER)
        session.add(owner_shop)
        session.commit()
        
        # Add mechanic first
        user_shop = UserShop(
            user_id=mechanic_user.id,
            shop_id=shop.id,
            role=ShopRole.MECHANIC
        )
        session.add(user_shop)
        session.commit()
        
        # Remove mechanic
        response = client.delete(
            f"/api/v1/shops/{shop.id}/members/{mechanic_user.id}",
            headers=owner_auth_headers
        )
        assert response.status_code == 200
        assert "removed" in response.json()["message"]
    
    def test_list_shop_mechanics(self, client: TestClient, session: Session, shop_owner, mechanic_user, owner_auth_headers):
        """Test listing shop mechanics."""
        shop = Shop(
            name="List Mechanics Shop",
            description="Test shop",
            address="123 St",
            owner_id=shop_owner.id
        )
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        # Create UserShop entry for owner
        owner_shop = UserShop(user_id=shop_owner.id, shop_id=shop.id, role=ShopRole.OWNER)
        session.add(owner_shop)
        session.commit()
        
        # Add mechanic
        user_shop = UserShop(
            user_id=mechanic_user.id,
            shop_id=shop.id,
            role=ShopRole.MECHANIC
        )
        session.add(user_shop)
        session.commit()
        
        response = client.get(
            f"/api/v1/shops/{shop.id}/members",
            headers=owner_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1  # At least the mechanic
