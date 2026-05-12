"""Tests for quotation system endpoints."""
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.shop import Shop, UserShop, ShopRole
from app.models.appointment import Appointment, AppointmentStatus
from app.models.quotation import Quotation, QuotationStatus


class TestQuotationCreation:
    """Test quotation creation by shop owners."""

    def test_create_quotation(self, client: TestClient, session: Session, shop_owner, customer_user, owner_auth_headers):
        """Test shop owner creating a quotation."""
        shop = Shop(name="Quote Shop", address="123 St")
        session.add(shop)
        session.commit()
        session.refresh(shop)

        # Add owner to shop
        user_shop = UserShop(user_id=shop_owner.id, shop_id=shop.id, role=ShopRole.OWNER)
        session.add(user_shop)
        session.commit()

        # Create appointment
        appointment = Appointment(
            shop_id=shop.id,
            customer_id=customer_user.id,
            appointment_date=datetime.utcnow() + timedelta(days=1),
            status=AppointmentStatus.CONFIRMED,
            service_price=50
        )
        session.add(appointment)
        session.commit()
        session.refresh(appointment)

        response = client.post(
            f"/api/v1/quotations/shops/{shop.id}",
            json={
                "shop_id": shop.id,
                "appointment_id": appointment.id,
                "title": "Engine Repair Estimate",
                "description": "Full engine diagnostics and repair",
                "items": [
                    {
                        "item_type": "labor",
                        "name": "Engine Diagnostics",
                        "description": "Full diagnostic scan",
                        "quantity": 1.0,
                        "unit_price": 75.0
                    },
                    {
                        "item_type": "part",
                        "name": "Spark Plugs",
                        "quantity": 4.0,
                        "unit_price": 12.5
                    }
                ],
                "labor_cost": 75.0,
                "parts_cost": 50.0,
                "tax_amount": 10.0,
                "discount_amount": 5.0
            },
            headers=owner_auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Engine Repair Estimate"
        assert data["total_amount"] == 255.0  # 75 labor + 50 parts + 125 items + 10 tax - 5 discount
        assert data["status"] == QuotationStatus.DRAFT

    def test_customer_cannot_create_quotation(self, client: TestClient, session: Session, shop_owner, customer_user, customer_auth_headers):
        """Test customer cannot create quotations."""
        shop = Shop(name="Quote Shop 2", address="123 St")
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

        response = client.post(
            f"/api/v1/quotations/shops/{shop.id}",
            json={
                "shop_id": shop.id,
                "appointment_id": appointment.id,
                "title": "Test Quote",
                "items": []
            },
            headers=customer_auth_headers
        )
        assert response.status_code == 403


class TestQuotationManagement:
    """Test quotation management by shop."""

    def test_send_quotation(self, client: TestClient, session: Session, shop_owner, customer_user, owner_auth_headers):
        """Test sending quotation to customer."""
        shop = Shop(name="Send Quote Shop", address="123 St")
        session.add(shop)
        session.commit()
        session.refresh(shop)

        user_shop = UserShop(user_id=shop_owner.id, shop_id=shop.id, role=ShopRole.OWNER)
        session.add(user_shop)
        session.commit()

        appointment = Appointment(
            shop_id=shop.id,
            customer_id=customer_user.id,
            appointment_date=datetime.utcnow() + timedelta(days=1),
            status=AppointmentStatus.CONFIRMED,
            service_price=50
        )
        session.add(appointment)
        session.commit()
        session.refresh(appointment)

        # Create quotation
        quotation = Quotation(
            shop_id=shop.id,
            customer_id=customer_user.id,
            appointment_id=appointment.id,
            title="Oil Change Quote",
            status=QuotationStatus.DRAFT,
            labor_cost=30.0,
            parts_cost=20.0,
            total_amount=50.0
        )
        session.add(quotation)
        session.commit()
        session.refresh(quotation)

        response = client.post(
            f"/api/v1/quotations/shops/{shop.id}/{quotation.id}/send",
            headers=owner_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == QuotationStatus.SENT

    def test_list_shop_quotations(self, client: TestClient, session: Session, shop_owner, customer_user, owner_auth_headers):
        """Test listing shop quotations."""
        shop = Shop(name="List Quote Shop", address="123 St")
        session.add(shop)
        session.commit()
        session.refresh(shop)

        user_shop = UserShop(user_id=shop_owner.id, shop_id=shop.id, role=ShopRole.OWNER)
        session.add(user_shop)
        session.commit()

        appointment = Appointment(
            shop_id=shop.id,
            customer_id=customer_user.id,
            appointment_date=datetime.utcnow() + timedelta(days=1),
            status=AppointmentStatus.CONFIRMED,
            service_price=50
        )
        session.add(appointment)
        session.commit()
        session.refresh(appointment)

        quotation = Quotation(
            shop_id=shop.id,
            customer_id=customer_user.id,
            appointment_id=appointment.id,
            title="Test Quote",
            status=QuotationStatus.SENT,
            total_amount=100.0
        )
        session.add(quotation)
        session.commit()

        response = client.get(
            f"/api/v1/quotations/shops/{shop.id}",
            headers=owner_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1


class TestCustomerQuotationActions:
    """Test customer quotation actions."""

    def test_customer_view_quotations(self, client: TestClient, session: Session, shop_owner, customer_user, customer_auth_headers):
        """Test customer viewing their quotations."""
        shop = Shop(name="Cust Quote Shop", address="123 St")
        session.add(shop)
        session.commit()
        session.refresh(shop)

        appointment = Appointment(
            shop_id=shop.id,
            customer_id=customer_user.id,
            appointment_date=datetime.utcnow() + timedelta(days=1),
            status=AppointmentStatus.CONFIRMED,
            service_price=50
        )
        session.add(appointment)
        session.commit()
        session.refresh(appointment)

        quotation = Quotation(
            shop_id=shop.id,
            customer_id=customer_user.id,
            appointment_id=appointment.id,
            title="Customer Quote",
            status=QuotationStatus.SENT,
            total_amount=75.0
        )
        session.add(quotation)
        session.commit()

        response = client.get(
            "/api/v1/quotations/my-quotations",
            headers=customer_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_customer_approve_quotation(self, client: TestClient, session: Session, shop_owner, customer_user, customer_auth_headers):
        """Test customer approving a quotation."""
        shop = Shop(name="Approve Quote Shop", address="123 St")
        session.add(shop)
        session.commit()
        session.refresh(shop)

        appointment = Appointment(
            shop_id=shop.id,
            customer_id=customer_user.id,
            appointment_date=datetime.utcnow() + timedelta(days=1),
            status=AppointmentStatus.CONFIRMED,
            service_price=50
        )
        session.add(appointment)
        session.commit()
        session.refresh(appointment)

        quotation = Quotation(
            shop_id=shop.id,
            customer_id=customer_user.id,
            appointment_id=appointment.id,
            title="Approve Me",
            status=QuotationStatus.SENT,
            total_amount=100.0
        )
        session.add(quotation)
        session.commit()
        session.refresh(quotation)

        response = client.post(
            f"/api/v1/quotations/my-quotations/{quotation.id}/action",
            json={"action": "approve"},
            headers=customer_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == QuotationStatus.APPROVED

    def test_customer_reject_quotation(self, client: TestClient, session: Session, shop_owner, customer_user, customer_auth_headers):
        """Test customer rejecting a quotation."""
        shop = Shop(name="Reject Quote Shop", address="123 St")
        session.add(shop)
        session.commit()
        session.refresh(shop)

        appointment = Appointment(
            shop_id=shop.id,
            customer_id=customer_user.id,
            appointment_date=datetime.utcnow() + timedelta(days=1),
            status=AppointmentStatus.CONFIRMED,
            service_price=50
        )
        session.add(appointment)
        session.commit()
        session.refresh(appointment)

        quotation = Quotation(
            shop_id=shop.id,
            customer_id=customer_user.id,
            appointment_id=appointment.id,
            title="Reject Me",
            status=QuotationStatus.SENT,
            total_amount=200.0
        )
        session.add(quotation)
        session.commit()
        session.refresh(quotation)

        response = client.post(
            f"/api/v1/quotations/my-quotations/{quotation.id}/action",
            json={"action": "reject", "rejection_reason": "Too expensive"},
            headers=customer_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == QuotationStatus.REJECTED
