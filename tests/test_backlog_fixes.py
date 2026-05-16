"""Tests for all API backlog fixes (P0/P1/P2 items from API_BACKLOG.md)."""
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.shop import Shop, UserShop
from app.models.appointment import Appointment, AppointmentStatus
from app.models.product_order import ProductOrder, OrderStatus


# ─── helpers ──────────────────────────────────────────────────────────────────

def _make_shop(session: Session, owner_id: int, name: str = "Test Shop") -> Shop:
    shop = Shop(name=name, address="1 Main St", is_active=True)
    session.add(shop)
    session.commit()
    session.refresh(shop)
    assert shop.id is not None
    _assign_member(session, owner_id, shop.id, "owner")
    return shop


def _assign_member(session: Session, user_id: int, shop_id: int, role: str) -> UserShop:
    us = UserShop(user_id=user_id, shop_id=shop_id, role=role, is_active=True)
    session.add(us)
    session.commit()
    session.refresh(us)
    return us


def _make_appointment(
    session: Session,
    shop_id: int,
    customer_id: int,
    appt_status: AppointmentStatus = AppointmentStatus.PENDING,
    total: float = 100.0,
) -> Appointment:
    appt = Appointment(
        shop_id=shop_id,
        customer_id=customer_id,
        appointment_date=datetime.utcnow() + timedelta(days=1),
        status=appt_status,
        service_price=total,
        total_amount=total,
    )
    session.add(appt)
    session.commit()
    session.refresh(appt)
    return appt


def _make_order(
    session: Session,
    shop_id: int,
    customer_id: int,
    order_status: OrderStatus = OrderStatus.PENDING,
    total: float = 50.0,
) -> ProductOrder:
    order = ProductOrder(
        shop_id=shop_id,
        customer_id=customer_id,
        status=order_status,
        total_amount=total,
    )
    session.add(order)
    session.commit()
    session.refresh(order)
    return order


# ─── P0-1: GET /auth/me/roles ─────────────────────────────────────────────────

class TestMeRoles:
    """P0-1: /auth/me/roles must reflect UserShop memberships."""

    def test_roles_no_shop_memberships(self, client: TestClient, auth_headers, test_user):
        """Regular user with no shop: roles contains only 'user', shop_roles is empty."""
        response = client.get("/api/v1/auth/me/roles", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "shop_roles" in data
        assert data["shop_roles"] == []
        assert "user" in data["roles"]

    def test_roles_as_shop_owner(
        self, client: TestClient, session: Session, shop_owner, owner_auth_headers
    ):
        """Shop owner: roles contains 'owner', shop_roles lists the shop."""
        shop = _make_shop(session, shop_owner.id)
        _assign_member(session, shop_owner.id, shop.id, "owner")

        response = client.get("/api/v1/auth/me/roles", headers=owner_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "owner" in data["roles"]
        assert any(sr["shop_id"] == shop.id and sr["role"] == "owner" for sr in data["shop_roles"])

    def test_roles_as_mechanic(
        self, client: TestClient, session: Session, shop_owner, mechanic_user, mechanic_auth_headers
    ):
        """Mechanic: roles contains 'mechanic', shop_roles lists correct shop."""
        shop = _make_shop(session, shop_owner.id)
        _assign_member(session, mechanic_user.id, shop.id, "mechanic")

        response = client.get("/api/v1/auth/me/roles", headers=mechanic_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "mechanic" in data["roles"]
        assert any(sr["role"] == "mechanic" for sr in data["shop_roles"])

    def test_roles_includes_multiple_shops(
        self, client: TestClient, session: Session, shop_owner, owner_auth_headers
    ):
        """Owner of two shops: shop_roles has two entries."""
        shop1 = _make_shop(session, shop_owner.id, "Shop A")
        shop2 = _make_shop(session, shop_owner.id, "Shop B")
        _assign_member(session, shop_owner.id, shop1.id, "owner")
        _assign_member(session, shop_owner.id, shop2.id, "owner")

        response = client.get("/api/v1/auth/me/roles", headers=owner_auth_headers)
        assert response.status_code == 200
        data = response.json()
        shop_ids = [sr["shop_id"] for sr in data["shop_roles"]]
        assert shop1.id in shop_ids
        assert shop2.id in shop_ids

    def test_roles_requires_auth(self, client: TestClient):
        """Unauthenticated request is rejected."""
        response = client.get("/api/v1/auth/me/roles")
        assert response.status_code == 401


# ─── P0-2: REJECTED status ───────────────────────────────────────────────────

class TestRejectedAppointmentStatus:
    """P0-2: Reject action sets status to 'rejected'; admin can filter by it."""

    def test_reject_action_sets_rejected_status(
        self,
        client: TestClient,
        session: Session,
        shop_owner,
        customer_user,
        owner_auth_headers,
    ):
        """Mechanic reject sets appointment status to 'rejected' (not 'cancelled')."""
        shop = _make_shop(session, shop_owner.id)
        _assign_member(session, shop_owner.id, shop.id, "owner")
        appt = _make_appointment(session, shop.id, customer_user.id)

        response = client.post(
            f"/api/v1/mechanic/shops/{shop.id}/bookings/{appt.id}/action",
            json={"action": "reject", "reason": "Not available"},
            headers=owner_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["new_status"] == "rejected"

        session.refresh(appt)
        assert appt.status == AppointmentStatus.REJECTED

    def test_admin_filter_rejected_returns_results(
        self,
        client: TestClient,
        session: Session,
        shop_owner,
        customer_user,
        admin_user,
        admin_auth_headers,
    ):
        """Admin can filter appointments by status=rejected."""
        shop = _make_shop(session, shop_owner.id)
        _make_appointment(session, shop.id, customer_user.id, AppointmentStatus.REJECTED)

        response = client.get(
            "/api/v1/admin/appointments?status=rejected",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert all(item["status"] == "rejected" for item in data["items"])

    def test_accept_action_still_sets_confirmed(
        self,
        client: TestClient,
        session: Session,
        shop_owner,
        customer_user,
        owner_auth_headers,
    ):
        """Accept action still sets status to 'confirmed'."""
        shop = _make_shop(session, shop_owner.id)
        _assign_member(session, shop_owner.id, shop.id, "owner")
        appt = _make_appointment(session, shop.id, customer_user.id)

        response = client.post(
            f"/api/v1/mechanic/shops/{shop.id}/bookings/{appt.id}/action",
            json={"action": "accept"},
            headers=owner_auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["new_status"] == "confirmed"


# ─── P1-3: GET /shops/{shop_id}/statistics ───────────────────────────────────

class TestShopStatistics:
    """P1-3: Shop statistics endpoint for owners."""

    def test_statistics_shape(
        self,
        client: TestClient,
        session: Session,
        shop_owner,
        owner_auth_headers,
    ):
        """Response contains all expected keys."""
        shop = _make_shop(session, shop_owner.id)
        _assign_member(session, shop_owner.id, shop.id, "owner")

        response = client.get(
            f"/api/v1/shops/{shop.id}/statistics",
            headers=owner_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["shop_id"] == shop.id
        for key in ("appointments", "orders", "revenue", "products", "services"):
            assert key in data
        for key in ("total", "pending", "confirmed", "completed", "cancelled", "rejected"):
            assert key in data["appointments"]
        for key in ("appointments", "orders", "total"):
            assert key in data["revenue"]

    def test_statistics_counts_correctly(
        self,
        client: TestClient,
        session: Session,
        shop_owner,
        customer_user,
        owner_auth_headers,
    ):
        """Counts reflect actual DB state."""
        shop = _make_shop(session, shop_owner.id)
        _assign_member(session, shop_owner.id, shop.id, "owner")
        _make_appointment(session, shop.id, customer_user.id, AppointmentStatus.PENDING)
        _make_appointment(session, shop.id, customer_user.id, AppointmentStatus.COMPLETED, 200.0)
        _make_order(session, shop.id, customer_user.id, OrderStatus.COMPLETED, 75.0)

        response = client.get(
            f"/api/v1/shops/{shop.id}/statistics",
            headers=owner_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["appointments"]["total"] == 2
        assert data["appointments"]["pending"] == 1
        assert data["appointments"]["completed"] == 1
        assert data["orders"]["completed"] == 1
        assert data["revenue"]["appointments"] == 200.0
        assert data["revenue"]["orders"] == 75.0
        assert data["revenue"]["total"] == 275.0

    def test_statistics_requires_membership(
        self,
        client: TestClient,
        session: Session,
        shop_owner,
        customer_user,
        customer_auth_headers,
    ):
        """Non-member cannot view shop statistics."""
        shop = _make_shop(session, shop_owner.id)
        response = client.get(
            f"/api/v1/shops/{shop.id}/statistics",
            headers=customer_auth_headers,
        )
        assert response.status_code == 403

    def test_statistics_unknown_shop(
        self, client: TestClient, owner_auth_headers
    ):
        """Non-existent shop returns 404."""
        response = client.get("/api/v1/shops/99999/statistics", headers=owner_auth_headers)
        assert response.status_code in (403, 404)


# ─── P1-5: Pagination for mechanic endpoints ─────────────────────────────────

class TestMechanicEndpointPagination:
    """P1-5: pending-bookings and pending-orders now support page/limit."""

    def test_pending_bookings_default_shape(
        self,
        client: TestClient,
        session: Session,
        shop_owner,
        customer_user,
        owner_auth_headers,
    ):
        """Response uses {total, page, limit, items} envelope."""
        shop = _make_shop(session, shop_owner.id)
        _assign_member(session, shop_owner.id, shop.id, "owner")

        response = client.get(
            f"/api/v1/mechanic/shops/{shop.id}/pending-bookings",
            headers=owner_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        for key in ("total", "page", "limit", "items"):
            assert key in data

    def test_pending_bookings_pagination(
        self,
        client: TestClient,
        session: Session,
        shop_owner,
        customer_user,
        owner_auth_headers,
    ):
        """Page/limit params slice results correctly."""
        shop = _make_shop(session, shop_owner.id)
        _assign_member(session, shop_owner.id, shop.id, "owner")
        for _ in range(3):
            _make_appointment(session, shop.id, customer_user.id)

        r1 = client.get(
            f"/api/v1/mechanic/shops/{shop.id}/pending-bookings?page=1&limit=2",
            headers=owner_auth_headers,
        )
        assert r1.status_code == 200
        d1 = r1.json()
        assert d1["total"] == 3
        assert len(d1["items"]) == 2
        assert d1["page"] == 1

        r2 = client.get(
            f"/api/v1/mechanic/shops/{shop.id}/pending-bookings?page=2&limit=2",
            headers=owner_auth_headers,
        )
        assert r2.status_code == 200
        d2 = r2.json()
        assert len(d2["items"]) == 1
        assert d2["page"] == 2

    def test_pending_orders_default_shape(
        self,
        client: TestClient,
        session: Session,
        shop_owner,
        customer_user,
        owner_auth_headers,
    ):
        """pending-orders uses {total, page, limit, items} envelope."""
        shop = _make_shop(session, shop_owner.id)
        _assign_member(session, shop_owner.id, shop.id, "owner")

        response = client.get(
            f"/api/v1/mechanic/shops/{shop.id}/pending-orders",
            headers=owner_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        for key in ("total", "page", "limit", "items"):
            assert key in data

    def test_pending_orders_pagination(
        self,
        client: TestClient,
        session: Session,
        shop_owner,
        customer_user,
        owner_auth_headers,
    ):
        """Page/limit params work on pending-orders."""
        shop = _make_shop(session, shop_owner.id)
        _assign_member(session, shop_owner.id, shop.id, "owner")
        for _ in range(4):
            _make_order(session, shop.id, customer_user.id)

        r = client.get(
            f"/api/v1/mechanic/shops/{shop.id}/pending-orders?page=1&limit=3",
            headers=owner_auth_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 4
        assert len(data["items"]) == 3


# ─── P1-6: PUT /admin/shops/{shop_id}/status ─────────────────────────────────

class TestAdminShopStatus:
    """P1-6: Admin can activate/deactivate a shop without deleting it."""

    def test_deactivate_shop(
        self,
        client: TestClient,
        session: Session,
        shop_owner,
        admin_user,
        admin_auth_headers,
    ):
        """Admin can deactivate an active shop."""
        shop = _make_shop(session, shop_owner.id)

        response = client.put(
            f"/api/v1/admin/shops/{shop.id}/status?is_active=false",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False
        assert "deactivated" in data["message"]

        session.refresh(shop)
        assert shop.is_active is False

    def test_activate_shop(
        self,
        client: TestClient,
        session: Session,
        shop_owner,
        admin_user,
        admin_auth_headers,
    ):
        """Admin can reactivate a deactivated shop."""
        shop = Shop(name="Inactive Shop", address="1 St", owner_id=shop_owner.id, is_active=False)
        session.add(shop)
        session.commit()
        session.refresh(shop)

        response = client.put(
            f"/api/v1/admin/shops/{shop.id}/status?is_active=true",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is True

        session.refresh(shop)
        assert shop.is_active is True

    def test_shop_status_non_admin_forbidden(
        self,
        client: TestClient,
        session: Session,
        shop_owner,
        owner_auth_headers,
    ):
        """Non-admin cannot call the shop status endpoint."""
        shop = _make_shop(session, shop_owner.id)
        response = client.put(
            f"/api/v1/admin/shops/{shop.id}/status?is_active=false",
            headers=owner_auth_headers,
        )
        assert response.status_code == 403

    def test_shop_status_not_found(
        self, client: TestClient, admin_user, admin_auth_headers
    ):
        """Returns 404 for unknown shop."""
        response = client.put(
            "/api/v1/admin/shops/99999/status?is_active=false",
            headers=admin_auth_headers,
        )
        assert response.status_code == 404


# ─── Response shape standardisation ──────────────────────────────────────────

class TestAdminResponseShapes:
    """All admin list endpoints must return {total, page, limit, items}."""

    def test_admin_users_shape(
        self, client: TestClient, admin_user, admin_auth_headers
    ):
        response = client.get("/api/v1/admin/users", headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        for key in ("total", "page", "limit", "items"):
            assert key in data, f"Missing key: {key}"
        assert "users" not in data

    def test_admin_users_pagination_params(
        self, client: TestClient, admin_user, admin_auth_headers
    ):
        """page/limit query params are respected."""
        response = client.get(
            "/api/v1/admin/users?page=1&limit=5", headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["limit"] == 5

    def test_admin_shops_shape(
        self,
        client: TestClient,
        session: Session,
        shop_owner,
        admin_user,
        admin_auth_headers,
    ):
        _make_shop(session, shop_owner.id)
        response = client.get("/api/v1/admin/shops", headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        for key in ("total", "page", "limit", "items"):
            assert key in data
        assert "shops" not in data

    def test_admin_shops_search(
        self,
        client: TestClient,
        session: Session,
        shop_owner,
        admin_user,
        admin_auth_headers,
    ):
        """search param filters shops by name (case-insensitive)."""
        _make_shop(session, shop_owner.id, "Unique Garage XYZ")
        _make_shop(session, shop_owner.id, "Another Place")

        response = client.get(
            "/api/v1/admin/shops?search=unique",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert all("unique" in item["name"].lower() for item in data["items"])

    def test_admin_appointments_shape(
        self,
        client: TestClient,
        session: Session,
        shop_owner,
        customer_user,
        admin_user,
        admin_auth_headers,
    ):
        shop = _make_shop(session, shop_owner.id)
        _make_appointment(session, shop.id, customer_user.id)

        response = client.get("/api/v1/admin/appointments", headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        for key in ("total", "page", "limit", "items"):
            assert key in data
        assert "appointments" not in data

    def test_admin_orders_shape(
        self,
        client: TestClient,
        session: Session,
        shop_owner,
        customer_user,
        admin_user,
        admin_auth_headers,
    ):
        shop = _make_shop(session, shop_owner.id)
        _make_order(session, shop.id, customer_user.id)

        response = client.get("/api/v1/admin/orders", headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        for key in ("total", "page", "limit", "items"):
            assert key in data
        assert "orders" not in data


# ─── P2-3: Daily statistics revenue ──────────────────────────────────────────

class TestDailyStatisticsRevenue:
    """P2-3: GET /admin/statistics/daily includes revenue breakdown."""

    def test_daily_stats_has_revenue(
        self, client: TestClient, admin_user, admin_auth_headers
    ):
        response = client.get(
            "/api/v1/admin/statistics/daily?days=30",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "revenue" in data
        for key in ("appointments", "orders", "total"):
            assert key in data["revenue"]

    def test_daily_stats_revenue_counts_completed(
        self,
        client: TestClient,
        session: Session,
        shop_owner,
        customer_user,
        admin_user,
        admin_auth_headers,
    ):
        """Revenue reflects only completed records within the period."""
        shop = _make_shop(session, shop_owner.id)
        _make_appointment(session, shop.id, customer_user.id, AppointmentStatus.COMPLETED, 300.0)
        _make_order(session, shop.id, customer_user.id, OrderStatus.COMPLETED, 120.0)

        response = client.get(
            "/api/v1/admin/statistics/daily?days=30",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["revenue"]["appointments"] >= 300.0
        assert data["revenue"]["orders"] >= 120.0
        assert data["revenue"]["total"] >= 420.0

    def test_daily_stats_revenue_excludes_non_completed(
        self,
        client: TestClient,
        session: Session,
        shop_owner,
        customer_user,
        admin_user,
        admin_auth_headers,
    ):
        """Pending/cancelled records do not inflate revenue."""
        shop = _make_shop(session, shop_owner.id)
        _make_appointment(session, shop.id, customer_user.id, AppointmentStatus.PENDING, 999.0)
        _make_order(session, shop.id, customer_user.id, OrderStatus.CANCELLED, 999.0)

        response = client.get(
            "/api/v1/admin/statistics/daily?days=1",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["revenue"]["appointments"] == 0.0
        assert data["revenue"]["orders"] == 0.0


# ─── GET /shops — merge conflict resolved (paginated) ────────────────────────

class TestShopsListPaginated:
    """Merge conflict resolved: GET /shops uses paginated {items, total, page, limit}."""

    def test_list_shops_shape(
        self,
        client: TestClient,
        session: Session,
        shop_owner,
    ):
        _make_shop(session, shop_owner.id)
        response = client.get("/api/v1/shops")
        assert response.status_code == 200
        data = response.json()
        for key in ("items", "total", "page", "limit"):
            assert key in data

    def test_list_shops_pagination(
        self,
        client: TestClient,
        session: Session,
        shop_owner,
    ):
        for i in range(3):
            _make_shop(session, shop_owner.id, f"Shop {i}")

        r = client.get("/api/v1/shops?page=1&limit=2")
        assert r.status_code == 200
        data = r.json()
        assert len(data["items"]) == 2
        assert data["total"] >= 3
