"""Tests for rating system."""
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.shop import Shop, UserShop, ShopRole
from app.models.product import Product, Service
from app.models.appointment import Appointment, AppointmentStatus
from app.models.product_order import ProductOrder, OrderStatus
from app.models.ratings import ProductRating, ServiceRating


class TestProductRatings:
    """Test product rating endpoints."""
    
    def test_rate_product(self, client: TestClient, session: Session, shop_owner, customer_user, customer_auth_headers):
        """Test customer rating a product."""
        shop = Shop(name="Rate Product Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        product = Product(name="Oil Filter", price=25, stock_quantity=100, shop_id=shop.id)
        session.add(product)
        session.commit()
        session.refresh(product)
        
        # Create completed order
        order = ProductOrder(
            shop_id=shop.id,
            customer_id=customer_user.id,
            status=OrderStatus.COMPLETED,
            total_amount=25
        )
        session.add(order)
        session.commit()
        session.refresh(order)
        
        response = client.post(
            "/api/v1/ratings/products",
            json={
                "product_id": product.id,
                "order_id": order.id,
                "rating": 5,
                "review": "Great quality product!"
            },
            headers=customer_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "rated successfully" in data["message"]
    
    def test_product_rating_summary(self, client: TestClient, session: Session, shop_owner, customer_user, customer_auth_headers):
        """Test getting product rating summary."""
        shop = Shop(name="Summary Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        product = Product(name="Brake Pad", price=45, stock_quantity=50, shop_id=shop.id)
        session.add(product)
        session.commit()
        session.refresh(product)
        
        # Add ratings
        for i in range(3):
            rating = ProductRating(
                product_id=product.id,
                customer_id=customer_user.id,
                rating=5
            )
            session.add(rating)
        session.commit()
        
        response = client.get(f"/api/v1/ratings/products/{product.id}/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["average_rating"] == 5.0
        assert data["total_ratings"] == 3
        assert data["five_star"] == 3
    
    def test_product_reviews_public(self, client: TestClient, session: Session, shop_owner, customer_user):
        """Test getting product reviews publicly."""
        shop = Shop(name="Reviews Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        product = Product(name="Air Filter", price=20, stock_quantity=30, shop_id=shop.id)
        session.add(product)
        session.commit()
        session.refresh(product)
        
        # Add review
        rating = ProductRating(
            product_id=product.id,
            customer_id=customer_user.id,
            rating=4,
            review="Good product, fast delivery"
        )
        session.add(rating)
        session.commit()
        
        response = client.get(f"/api/v1/ratings/products/{product.id}/reviews")
        assert response.status_code == 200
        data = response.json()
        assert len(data["reviews"]) >= 1
        assert data["reviews"][0]["review"] == "Good product, fast delivery"


class TestServiceRatings:
    """Test service rating endpoints."""
    
    def test_rate_service(self, client: TestClient, session: Session, shop_owner, customer_user, customer_auth_headers):
        """Test customer rating a service."""
        shop = Shop(name="Rate Service Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        service = Service(name="Oil Change", price=50, shop_id=shop.id)
        session.add(service)
        session.commit()
        session.refresh(service)
        
        # Create completed appointment
        appointment = Appointment(
            shop_id=shop.id,
            customer_id=customer_user.id,
            service_id=service.id,
            appointment_date=datetime.utcnow() - timedelta(days=1),
            status=AppointmentStatus.COMPLETED,
            service_price=50
        )
        session.add(appointment)
        session.commit()
        session.refresh(appointment)
        
        response = client.post(
            "/api/v1/ratings/services",
            json={
                "service_id": service.id,
                "appointment_id": appointment.id,
                "rating": 5,
                "review": "Excellent service, very professional!"
            },
            headers=customer_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "rated successfully" in data["message"]
    
    def test_service_rating_summary(self, client: TestClient, session: Session, shop_owner, customer_user):
        """Test getting service rating summary."""
        shop = Shop(name="Service Summary Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        service = Service(name="Tire Rotation", price=30, shop_id=shop.id)
        session.add(service)
        session.commit()
        session.refresh(service)
        
        # Add ratings
        ratings = [5, 4, 5, 5, 4]
        for r in ratings:
            rating = ServiceRating(
                service_id=service.id,
                customer_id=customer_user.id,
                rating=r
            )
            session.add(rating)
        session.commit()
        
        response = client.get(f"/api/v1/ratings/services/{service.id}/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["average_rating"] == 4.6
        assert data["total_ratings"] == 5
        assert data["five_star"] == 3
        assert data["four_star"] == 2


class TestOwnerRatingViews:
    """Test owner viewing top rated items."""
    
    def test_owner_view_top_rated_products(self, client: TestClient, session: Session, shop_owner, customer_user, owner_auth_headers, customer_auth_headers):
        """Test owner viewing top rated products."""
        shop = Shop(name="Top Products Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        # Create UserShop entry for owner
        user_shop = UserShop(user_id=shop_owner.id, shop_id=shop.id, role=ShopRole.OWNER)
        session.add(user_shop)
        session.commit()
        
        # Create products with ratings
        products = [
            ("Product A", 4.5),
            ("Product B", 5.0),
            ("Product C", 3.5)
        ]
        
        for name, avg_rating in products:
            product = Product(name=name, price=20, stock_quantity=10, shop_id=shop.id)
            session.add(product)
            session.commit()
            session.refresh(product)
            
            # Add rating
            rating = ProductRating(
                product_id=product.id,
                customer_id=customer_user.id,
                rating=int(avg_rating)
            )
            session.add(rating)
        session.commit()
        
        response = client.get(
            f"/api/v1/ratings/shops/{shop.id}/top-products",
            headers=owner_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["top_products"]) >= 1
        # Should be sorted by rating
        assert data["top_products"][0]["name"] == "Product B"
    
    def test_owner_view_top_rated_services(self, client: TestClient, session: Session, shop_owner, customer_user, owner_auth_headers):
        """Test owner viewing top rated services."""
        shop = Shop(name="Top Services Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        # Create UserShop entry for owner
        user_shop = UserShop(user_id=shop_owner.id, shop_id=shop.id, role=ShopRole.OWNER)
        session.add(user_shop)
        session.commit()
        
        # Create services with ratings
        services = [
            ("Service A", 4),
            ("Service B", 5),
            ("Service C", 3)
        ]
        
        for name, rating_val in services:
            service = Service(name=name, price=50, shop_id=shop.id)
            session.add(service)
            session.commit()
            session.refresh(service)
            
            # Add rating
            rating = ServiceRating(
                service_id=service.id,
                customer_id=customer_user.id,
                rating=rating_val
            )
            session.add(rating)
        session.commit()
        
        response = client.get(
            f"/api/v1/ratings/shops/{shop.id}/top-services",
            headers=owner_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["top_services"]) >= 1
        assert data["top_services"][0]["name"] == "Service B"


class TestCustomerMyRatings:
    """Test customer viewing their ratings."""
    
    def test_customer_view_my_ratings(self, client: TestClient, session: Session, shop_owner, customer_user, customer_auth_headers):
        """Test customer viewing all their ratings."""
        shop = Shop(name="My Ratings Shop", address="123 St", owner_id=shop_owner.id)
        session.add(shop)
        session.commit()
        session.refresh(shop)
        
        # Create and rate product
        product = Product(name="Rated Product", price=25, shop_id=shop.id)
        session.add(product)
        session.commit()
        session.refresh(product)
        
        product_rating = ProductRating(
            product_id=product.id,
            customer_id=customer_user.id,
            rating=5,
            review="Great!"
        )
        session.add(product_rating)
        
        # Create and rate service
        service = Service(name="Rated Service", price=50, shop_id=shop.id)
        session.add(service)
        session.commit()
        session.refresh(service)
        
        service_rating = ServiceRating(
            service_id=service.id,
            customer_id=customer_user.id,
            rating=4,
            review="Good service"
        )
        session.add(service_rating)
        session.commit()
        
        response = client.get(
            "/api/v1/ratings/my-ratings",
            headers=customer_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["product_ratings"]) == 1
        assert len(data["service_ratings"]) == 1
