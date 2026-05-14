"""Tests for browse endpoints and global search.

Covers:
- GET /shops (paginated envelope)
- GET /customers/shops/{id}/browse/products
- GET /customers/shops/{id}/browse/services
- GET /customers/shops/{id}/browse/products/{product_id}
- GET /customers/shops/{id}/browse/services/{service_id}
- GET /search
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.shop import Shop
from app.models.product import Product, Service, ServiceType
from app.models.ratings import ProductRating, ServiceRating


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(name="shop")
def shop_fixture(session: Session) -> Shop:
    s = Shop(
        name="Test Garage",
        description="A well-known garage",
        address="123 Main St",
        phone="+1234567890",
        email="garage@test.com",
        is_active=True,
    )
    session.add(s)
    session.commit()
    session.refresh(s)
    return s


@pytest.fixture(name="inactive_shop")
def inactive_shop_fixture(session: Session) -> Shop:
    s = Shop(name="Closed Garage", address="999 Nowhere", is_active=False)
    session.add(s)
    session.commit()
    session.refresh(s)
    return s


@pytest.fixture(name="product")
def product_fixture(session: Session, shop: Shop) -> Product:
    p = Product(
        name="Oil Filter",
        description="OEM quality oil filter",
        price=15.99,
        stock_quantity=20,
        shop_id=shop.id,
        is_active=True,
    )
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


@pytest.fixture(name="service")
def service_fixture(session: Session, shop: Shop) -> Service:
    s = Service(
        name="Oil Change",
        description="Full synthetic oil change service",
        price=49.99,
        duration_minutes=30,
        shop_id=shop.id,
        service_type=ServiceType.SHOP_BASED,
        is_active=True,
    )
    session.add(s)
    session.commit()
    session.refresh(s)
    return s


@pytest.fixture(name="product_with_ratings")
def product_with_ratings_fixture(
    session: Session, shop: Shop, customer_user
) -> Product:
    p = Product(
        name="Spark Plug Set",
        description="High performance spark plugs",
        price=25.00,
        stock_quantity=10,
        shop_id=shop.id,
        is_active=True,
    )
    session.add(p)
    session.commit()
    session.refresh(p)

    for stars in [4, 5, 5]:
        session.add(ProductRating(product_id=p.id, customer_id=customer_user.id, rating=stars))
    session.commit()
    return p


@pytest.fixture(name="service_with_ratings")
def service_with_ratings_fixture(
    session: Session, shop: Shop, customer_user
) -> Service:
    s = Service(
        name="Tire Rotation",
        description="Four-wheel tire rotation",
        price=39.99,
        duration_minutes=45,
        shop_id=shop.id,
        service_type=ServiceType.SHOP_BASED,
        is_active=True,
    )
    session.add(s)
    session.commit()
    session.refresh(s)

    for stars in [5, 4]:
        session.add(ServiceRating(service_id=s.id, customer_id=customer_user.id, rating=stars))
    session.commit()
    return s


# ===========================================================================
# GET /shops — paginated envelope
# ===========================================================================

class TestShopsListPaginated:
    """GET /shops now returns a paginated envelope."""

    def test_returns_paginated_envelope(self, client: TestClient, session: Session, shop: Shop):
        response = client.get("/api/v1/shops")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data

    def test_items_contains_shop(self, client: TestClient, session: Session, shop: Shop):
        response = client.get("/api/v1/shops")
        data = response.json()
        names = [s["name"] for s in data["items"]]
        assert "Test Garage" in names

    def test_total_reflects_active_shops(self, client: TestClient, session: Session, shop: Shop, inactive_shop: Shop):
        response = client.get("/api/v1/shops")
        data = response.json()
        # inactive_shop should not be counted
        assert data["total"] >= 1
        names = [s["name"] for s in data["items"]]
        assert "Closed Garage" not in names

    def test_pagination_defaults(self, client: TestClient, session: Session, shop: Shop):
        response = client.get("/api/v1/shops")
        data = response.json()
        assert data["page"] == 1
        assert data["limit"] == 20

    def test_custom_page_and_limit(self, client: TestClient, session: Session):
        for i in range(5):
            session.add(Shop(name=f"Shop {i}", address=f"{i} St", is_active=True))
        session.commit()

        response = client.get("/api/v1/shops?page=1&limit=2")
        data = response.json()
        assert data["page"] == 1
        assert data["limit"] == 2
        assert len(data["items"]) <= 2

    def test_public_no_auth_required(self, client: TestClient, session: Session, shop: Shop):
        response = client.get("/api/v1/shops")
        assert response.status_code == 200


# ===========================================================================
# GET /customers/shops/{id}/browse/products
# ===========================================================================

class TestBrowseProducts:
    """Public product browse endpoint with search, pagination, ratings."""

    def test_returns_paginated_envelope(self, client: TestClient, product: Product, shop: Shop):
        response = client.get(f"/api/v1/customers/shops/{shop.id}/browse/products")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data

    def test_no_auth_required(self, client: TestClient, shop: Shop, product: Product):
        response = client.get(f"/api/v1/customers/shops/{shop.id}/browse/products")
        assert response.status_code == 200

    def test_lists_active_product(self, client: TestClient, shop: Shop, product: Product):
        response = client.get(f"/api/v1/customers/shops/{shop.id}/browse/products")
        data = response.json()
        assert data["total"] >= 1
        names = [p["name"] for p in data["items"]]
        assert "Oil Filter" in names

    def test_inactive_product_excluded(self, client: TestClient, session: Session, shop: Shop, product: Product):
        product.is_active = False
        session.commit()
        response = client.get(f"/api/v1/customers/shops/{shop.id}/browse/products")
        data = response.json()
        names = [p["name"] for p in data["items"]]
        assert "Oil Filter" not in names

    def test_search_by_name(self, client: TestClient, shop: Shop, product: Product):
        response = client.get(
            f"/api/v1/customers/shops/{shop.id}/browse/products?search=oil"
        )
        data = response.json()
        assert data["total"] >= 1
        assert any("Oil" in p["name"] for p in data["items"])

    def test_search_by_description(self, client: TestClient, shop: Shop, product: Product):
        response = client.get(
            f"/api/v1/customers/shops/{shop.id}/browse/products?search=OEM"
        )
        data = response.json()
        assert data["total"] >= 1

    def test_search_no_match_returns_empty(self, client: TestClient, shop: Shop, product: Product):
        response = client.get(
            f"/api/v1/customers/shops/{shop.id}/browse/products?search=zzznomatch"
        )
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_legacy_q_param_still_works(self, client: TestClient, shop: Shop, product: Product):
        response = client.get(
            f"/api/v1/customers/shops/{shop.id}/browse/products?q=oil"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    def test_response_includes_required_fields(self, client: TestClient, shop: Shop, product: Product):
        response = client.get(f"/api/v1/customers/shops/{shop.id}/browse/products")
        item = response.json()["items"][0]
        for field in ("id", "name", "price", "is_available", "stock_quantity", "rating", "rating_count"):
            assert field in item, f"Missing field: {field}"

    def test_rating_fields_default_zero_when_no_ratings(
        self, client: TestClient, shop: Shop, product: Product
    ):
        response = client.get(f"/api/v1/customers/shops/{shop.id}/browse/products")
        item = response.json()["items"][0]
        assert item["rating"] == 0.0
        assert item["rating_count"] == 0

    def test_rating_fields_populated_when_ratings_exist(
        self, client: TestClient, shop: Shop, product_with_ratings: Product
    ):
        response = client.get(f"/api/v1/customers/shops/{shop.id}/browse/products")
        items = response.json()["items"]
        rated = next(i for i in items if i["name"] == "Spark Plug Set")
        assert rated["rating"] > 0
        assert rated["rating_count"] == 3

    def test_pagination_limit(self, client: TestClient, session: Session, shop: Shop):
        for i in range(5):
            session.add(Product(name=f"Part {i}", price=10, stock_quantity=5, shop_id=shop.id))
        session.commit()

        response = client.get(
            f"/api/v1/customers/shops/{shop.id}/browse/products?page=1&limit=2"
        )
        data = response.json()
        assert len(data["items"]) <= 2
        assert data["limit"] == 2

    def test_empty_shop_returns_zero_total(self, client: TestClient, session: Session):
        empty_shop = Shop(name="Empty Shop", address="1 St", is_active=True)
        session.add(empty_shop)
        session.commit()
        session.refresh(empty_shop)

        response = client.get(f"/api/v1/customers/shops/{empty_shop.id}/browse/products")
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []


# ===========================================================================
# GET /customers/shops/{id}/browse/services
# ===========================================================================

class TestBrowseServices:
    """Public service browse endpoint."""

    def test_returns_paginated_envelope(self, client: TestClient, shop: Shop, service: Service):
        response = client.get(f"/api/v1/customers/shops/{shop.id}/browse/services")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_no_auth_required(self, client: TestClient, shop: Shop, service: Service):
        response = client.get(f"/api/v1/customers/shops/{shop.id}/browse/services")
        assert response.status_code == 200

    def test_lists_active_service(self, client: TestClient, shop: Shop, service: Service):
        data = client.get(f"/api/v1/customers/shops/{shop.id}/browse/services").json()
        assert data["total"] >= 1
        assert any(s["name"] == "Oil Change" for s in data["items"])

    def test_uses_estimated_duration_minutes_field(
        self, client: TestClient, shop: Shop, service: Service
    ):
        data = client.get(f"/api/v1/customers/shops/{shop.id}/browse/services").json()
        item = data["items"][0]
        assert "estimated_duration_minutes" in item
        assert "duration_minutes" not in item
        assert item["estimated_duration_minutes"] == 30

    def test_search_by_name(self, client: TestClient, shop: Shop, service: Service):
        data = client.get(
            f"/api/v1/customers/shops/{shop.id}/browse/services?search=oil"
        ).json()
        assert data["total"] >= 1

    def test_search_no_match_returns_empty(self, client: TestClient, shop: Shop, service: Service):
        data = client.get(
            f"/api/v1/customers/shops/{shop.id}/browse/services?search=zzznomatch"
        ).json()
        assert data["total"] == 0

    def test_response_includes_required_fields(self, client: TestClient, shop: Shop, service: Service):
        item = client.get(f"/api/v1/customers/shops/{shop.id}/browse/services").json()["items"][0]
        for field in ("id", "name", "price", "estimated_duration_minutes", "service_type", "is_available", "rating", "rating_count"):
            assert field in item, f"Missing field: {field}"

    def test_rating_fields_default_zero(self, client: TestClient, shop: Shop, service: Service):
        item = client.get(f"/api/v1/customers/shops/{shop.id}/browse/services").json()["items"][0]
        assert item["rating"] == 0.0
        assert item["rating_count"] == 0

    def test_rating_fields_populated(
        self, client: TestClient, shop: Shop, service_with_ratings: Service
    ):
        items = client.get(f"/api/v1/customers/shops/{shop.id}/browse/services").json()["items"]
        rated = next(s for s in items if s["name"] == "Tire Rotation")
        assert rated["rating"] == 4.5
        assert rated["rating_count"] == 2

    def test_inactive_service_excluded(
        self, client: TestClient, session: Session, shop: Shop, service: Service
    ):
        service.is_active = False
        session.commit()
        data = client.get(f"/api/v1/customers/shops/{shop.id}/browse/services").json()
        names = [s["name"] for s in data["items"]]
        assert "Oil Change" not in names


# ===========================================================================
# GET /customers/shops/{id}/browse/products/{product_id}
# ===========================================================================

class TestBrowseProductDetail:
    """Single-product detail endpoint."""

    def test_returns_product(self, client: TestClient, shop: Shop, product: Product):
        response = client.get(
            f"/api/v1/customers/shops/{shop.id}/browse/products/{product.id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == product.id
        assert data["name"] == "Oil Filter"
        assert data["price"] == 15.99

    def test_no_auth_required(self, client: TestClient, shop: Shop, product: Product):
        response = client.get(
            f"/api/v1/customers/shops/{shop.id}/browse/products/{product.id}"
        )
        assert response.status_code == 200

    def test_includes_rating_fields(self, client: TestClient, shop: Shop, product: Product):
        data = client.get(
            f"/api/v1/customers/shops/{shop.id}/browse/products/{product.id}"
        ).json()
        assert "rating" in data
        assert "rating_count" in data
        assert data["rating"] == 0.0
        assert data["rating_count"] == 0

    def test_includes_rating_data_when_rated(
        self, client: TestClient, shop: Shop, product_with_ratings: Product
    ):
        data = client.get(
            f"/api/v1/customers/shops/{shop.id}/browse/products/{product_with_ratings.id}"
        ).json()
        assert data["rating"] > 0
        assert data["rating_count"] == 3

    def test_not_found_unknown_id(self, client: TestClient, shop: Shop):
        response = client.get(f"/api/v1/customers/shops/{shop.id}/browse/products/99999")
        assert response.status_code == 404

    def test_not_found_wrong_shop(
        self, client: TestClient, session: Session, shop: Shop, product: Product
    ):
        other_shop = Shop(name="Other Shop", address="2 St", is_active=True)
        session.add(other_shop)
        session.commit()
        session.refresh(other_shop)

        response = client.get(
            f"/api/v1/customers/shops/{other_shop.id}/browse/products/{product.id}"
        )
        assert response.status_code == 404

    def test_inactive_product_returns_404(
        self, client: TestClient, session: Session, shop: Shop, product: Product
    ):
        product.is_active = False
        session.commit()
        response = client.get(
            f"/api/v1/customers/shops/{shop.id}/browse/products/{product.id}"
        )
        assert response.status_code == 404


# ===========================================================================
# GET /customers/shops/{id}/browse/services/{service_id}
# ===========================================================================

class TestBrowseServiceDetail:
    """Single-service detail endpoint."""

    def test_returns_service(self, client: TestClient, shop: Shop, service: Service):
        response = client.get(
            f"/api/v1/customers/shops/{shop.id}/browse/services/{service.id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == service.id
        assert data["name"] == "Oil Change"
        assert data["price"] == 49.99

    def test_no_auth_required(self, client: TestClient, shop: Shop, service: Service):
        response = client.get(
            f"/api/v1/customers/shops/{shop.id}/browse/services/{service.id}"
        )
        assert response.status_code == 200

    def test_uses_estimated_duration_minutes(self, client: TestClient, shop: Shop, service: Service):
        data = client.get(
            f"/api/v1/customers/shops/{shop.id}/browse/services/{service.id}"
        ).json()
        assert "estimated_duration_minutes" in data
        assert data["estimated_duration_minutes"] == 30

    def test_includes_rating_fields(self, client: TestClient, shop: Shop, service: Service):
        data = client.get(
            f"/api/v1/customers/shops/{shop.id}/browse/services/{service.id}"
        ).json()
        assert data["rating"] == 0.0
        assert data["rating_count"] == 0

    def test_includes_rating_data_when_rated(
        self, client: TestClient, shop: Shop, service_with_ratings: Service
    ):
        data = client.get(
            f"/api/v1/customers/shops/{shop.id}/browse/services/{service_with_ratings.id}"
        ).json()
        assert data["rating"] == 4.5
        assert data["rating_count"] == 2

    def test_not_found_unknown_id(self, client: TestClient, shop: Shop):
        response = client.get(f"/api/v1/customers/shops/{shop.id}/browse/services/99999")
        assert response.status_code == 404

    def test_not_found_wrong_shop(
        self, client: TestClient, session: Session, shop: Shop, service: Service
    ):
        other_shop = Shop(name="Other Shop 2", address="3 St", is_active=True)
        session.add(other_shop)
        session.commit()
        session.refresh(other_shop)

        response = client.get(
            f"/api/v1/customers/shops/{other_shop.id}/browse/services/{service.id}"
        )
        assert response.status_code == 404

    def test_inactive_service_returns_404(
        self, client: TestClient, session: Session, shop: Shop, service: Service
    ):
        service.is_active = False
        session.commit()
        response = client.get(
            f"/api/v1/customers/shops/{shop.id}/browse/services/{service.id}"
        )
        assert response.status_code == 404


# ===========================================================================
# GET /search — global cross-shop search
# ===========================================================================

class TestGlobalSearch:
    """Global search across all active shops."""

    def test_q_is_required(self, client: TestClient):
        response = client.get("/api/v1/search")
        assert response.status_code == 422

    def test_no_auth_required(self, client: TestClient, shop: Shop, product: Product):
        response = client.get("/api/v1/search?q=oil")
        assert response.status_code == 200

    def test_returns_paginated_envelope(self, client: TestClient, shop: Shop, product: Product):
        response = client.get("/api/v1/search?q=oil")
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data

    def test_finds_product_by_name(self, client: TestClient, shop: Shop, product: Product):
        data = client.get("/api/v1/search?q=oil&type=products").json()
        assert data["total"] >= 1
        assert any(i["name"] == "Oil Filter" for i in data["items"])

    def test_finds_service_by_name(self, client: TestClient, shop: Shop, service: Service):
        data = client.get("/api/v1/search?q=oil&type=services").json()
        assert data["total"] >= 1
        assert any(i["name"] == "Oil Change" for i in data["items"])

    def test_type_products_excludes_services(
        self, client: TestClient, shop: Shop, product: Product, service: Service
    ):
        data = client.get("/api/v1/search?q=oil&type=products").json()
        for item in data["items"]:
            assert item["type"] == "product"

    def test_type_services_excludes_products(
        self, client: TestClient, shop: Shop, product: Product, service: Service
    ):
        data = client.get("/api/v1/search?q=oil&type=services").json()
        for item in data["items"]:
            assert item["type"] == "service"

    def test_type_all_returns_both_types(
        self, client: TestClient, shop: Shop, product: Product, service: Service
    ):
        data = client.get("/api/v1/search?q=oil&type=all").json()
        types_found = {i["type"] for i in data["items"]}
        assert "product" in types_found
        assert "service" in types_found

    def test_invalid_type_rejected(self, client: TestClient):
        response = client.get("/api/v1/search?q=oil&type=invalid")
        assert response.status_code == 422

    def test_no_results_for_unknown_term(self, client: TestClient, shop: Shop, product: Product):
        data = client.get("/api/v1/search?q=zzznomatch").json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_each_item_includes_shop_info(
        self, client: TestClient, shop: Shop, product: Product
    ):
        data = client.get("/api/v1/search?q=oil&type=products").json()
        assert data["total"] >= 1
        item = data["items"][0]
        assert "shop" in item
        assert "id" in item["shop"]
        assert "name" in item["shop"]
        assert item["shop"]["name"] == "Test Garage"

    def test_product_item_fields(self, client: TestClient, shop: Shop, product: Product):
        data = client.get("/api/v1/search?q=oil&type=products").json()
        item = data["items"][0]
        for field in ("type", "id", "name", "price", "is_available", "stock_quantity", "rating", "rating_count", "shop"):
            assert field in item, f"Missing field: {field}"

    def test_service_item_fields(self, client: TestClient, shop: Shop, service: Service):
        data = client.get("/api/v1/search?q=oil&type=services").json()
        item = data["items"][0]
        for field in ("type", "id", "name", "price", "estimated_duration_minutes", "service_type", "is_available", "rating", "rating_count", "shop"):
            assert field in item, f"Missing field: {field}"

    def test_inactive_shop_products_excluded(
        self, client: TestClient, session: Session, inactive_shop: Shop
    ):
        p = Product(name="Oil from Closed Shop", price=5, stock_quantity=1, shop_id=inactive_shop.id)
        session.add(p)
        session.commit()

        data = client.get("/api/v1/search?q=closed+shop").json()
        assert data["total"] == 0

    def test_rating_data_included_for_rated_product(
        self, client: TestClient, shop: Shop, product_with_ratings: Product
    ):
        data = client.get("/api/v1/search?q=spark&type=products").json()
        assert data["total"] >= 1
        item = data["items"][0]
        assert item["rating"] > 0
        assert item["rating_count"] == 3

    def test_pagination_defaults(self, client: TestClient, shop: Shop, product: Product):
        data = client.get("/api/v1/search?q=oil").json()
        assert data["page"] == 1
        assert data["limit"] == 20
