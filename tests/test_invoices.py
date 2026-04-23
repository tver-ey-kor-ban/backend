"""Tests for invoice system endpoints."""
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.shop import Shop, UserShop, ShopRole
from app.models.invoice import Invoice, InvoiceItem, Payment, InvoiceStatus, PaymentMethod


class TestInvoiceCreation:
    """Test invoice creation by shop."""

    def test_create_invoice(self, client: TestClient, session: Session, shop_owner, customer_user, owner_auth_headers):
        """Test shop owner creating an invoice."""
        shop = Shop(name="Invoice Shop", address="123 St")
        session.add(shop)
        session.commit()
        session.refresh(shop)

        user_shop = UserShop(user_id=shop_owner.id, shop_id=shop.id, role=ShopRole.OWNER)
        session.add(user_shop)
        session.commit()

        response = client.post(
            f"/api/v1/invoices/shops/{shop.id}",
            json={
                "shop_id": shop.id,
                "customer_id": customer_user.id,
                "invoice_number": "INV-001",
                "items": [
                    {
                        "item_type": "labor",
                        "name": "Oil Change Labor",
                        "quantity": 1.0,
                        "unit_price": 35.0
                    },
                    {
                        "item_type": "part",
                        "name": "Oil Filter",
                        "quantity": 1.0,
                        "unit_price": 15.0
                    }
                ],
                "labor_cost": 35.0,
                "parts_cost": 15.0,
                "tax_amount": 5.0,
                "discount_amount": 0.0,
                "total_amount": 55.0,
                "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat()
            },
            headers=owner_auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["invoice_number"] == "INV-001"
        assert data["total_amount"] == 55.0
        assert data["status"] == InvoiceStatus.DRAFT

    def test_duplicate_invoice_number(self, client: TestClient, session: Session, shop_owner, customer_user, owner_auth_headers):
        """Test cannot create invoice with duplicate number."""
        shop = Shop(name="Invoice Shop 2", address="123 St")
        session.add(shop)
        session.commit()
        session.refresh(shop)

        user_shop = UserShop(user_id=shop_owner.id, shop_id=shop.id, role=ShopRole.OWNER)
        session.add(user_shop)
        session.commit()

        invoice = Invoice(
            shop_id=shop.id,
            customer_id=customer_user.id,
            invoice_number="INV-DUP",
            total_amount=100.0,
            status=InvoiceStatus.DRAFT
        )
        session.add(invoice)
        session.commit()

        response = client.post(
            f"/api/v1/invoices/shops/{shop.id}",
            json={
                "shop_id": shop.id,
                "customer_id": customer_user.id,
                "invoice_number": "INV-DUP",
                "items": [],
                "total_amount": 100.0
            },
            headers=owner_auth_headers
        )
        assert response.status_code == 400


class TestInvoiceManagement:
    """Test invoice management by shop."""

    def test_send_invoice(self, client: TestClient, session: Session, shop_owner, customer_user, owner_auth_headers):
        """Test sending invoice to customer."""
        shop = Shop(name="Send Inv Shop", address="123 St")
        session.add(shop)
        session.commit()
        session.refresh(shop)

        user_shop = UserShop(user_id=shop_owner.id, shop_id=shop.id, role=ShopRole.OWNER)
        session.add(user_shop)
        session.commit()

        invoice = Invoice(
            shop_id=shop.id,
            customer_id=customer_user.id,
            invoice_number="INV-SEND-001",
            total_amount=100.0,
            status=InvoiceStatus.DRAFT
        )
        session.add(invoice)
        session.commit()
        session.refresh(invoice)

        response = client.post(
            f"/api/v1/invoices/shops/{shop.id}/{invoice.id}/send",
            headers=owner_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == InvoiceStatus.SENT

    def test_record_payment(self, client: TestClient, session: Session, shop_owner, customer_user, owner_auth_headers):
        """Test recording a payment."""
        shop = Shop(name="Payment Shop", address="123 St")
        session.add(shop)
        session.commit()
        session.refresh(shop)

        user_shop = UserShop(user_id=shop_owner.id, shop_id=shop.id, role=ShopRole.OWNER)
        session.add(user_shop)
        session.commit()

        invoice = Invoice(
            shop_id=shop.id,
            customer_id=customer_user.id,
            invoice_number="INV-PAY-001",
            total_amount=100.0,
            amount_paid=0.0,
            status=InvoiceStatus.SENT
        )
        session.add(invoice)
        session.commit()
        session.refresh(invoice)

        response = client.post(
            f"/api/v1/invoices/shops/{shop.id}/{invoice.id}/payments",
            json={
                "amount": 100.0,
                "method": "cash",
                "reference": "REF-001",
                "notes": "Full payment"
            },
            headers=owner_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["amount_paid"] == 100.0
        assert data["balance_due"] == 0.0
        assert data["status"] == InvoiceStatus.PAID

    def test_partial_payment(self, client: TestClient, session: Session, shop_owner, customer_user, owner_auth_headers):
        """Test recording a partial payment."""
        shop = Shop(name="Partial Shop", address="123 St")
        session.add(shop)
        session.commit()
        session.refresh(shop)

        user_shop = UserShop(user_id=shop_owner.id, shop_id=shop.id, role=ShopRole.OWNER)
        session.add(user_shop)
        session.commit()

        invoice = Invoice(
            shop_id=shop.id,
            customer_id=customer_user.id,
            invoice_number="INV-PART-001",
            total_amount=100.0,
            amount_paid=0.0,
            status=InvoiceStatus.SENT
        )
        session.add(invoice)
        session.commit()
        session.refresh(invoice)

        response = client.post(
            f"/api/v1/invoices/shops/{shop.id}/{invoice.id}/payments",
            json={
                "amount": 50.0,
                "method": "card"
            },
            headers=owner_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["amount_paid"] == 50.0
        assert data["balance_due"] == 50.0
        assert data["status"] == InvoiceStatus.PARTIALLY_PAID


class TestCustomerInvoiceView:
    """Test customer viewing invoices."""

    def test_customer_view_invoices(self, client: TestClient, session: Session, shop_owner, customer_user, customer_auth_headers):
        """Test customer viewing their invoices."""
        shop = Shop(name="Cust Inv Shop", address="123 St")
        session.add(shop)
        session.commit()
        session.refresh(shop)

        invoice = Invoice(
            shop_id=shop.id,
            customer_id=customer_user.id,
            invoice_number="INV-CUST-001",
            total_amount=150.0,
            status=InvoiceStatus.SENT
        )
        session.add(invoice)
        session.commit()

        response = client.get(
            "/api/v1/invoices/my-invoices",
            headers=customer_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_customer_view_invoice_detail(self, client: TestClient, session: Session, shop_owner, customer_user, customer_auth_headers):
        """Test customer viewing specific invoice."""
        shop = Shop(name="Detail Inv Shop", address="123 St")
        session.add(shop)
        session.commit()
        session.refresh(shop)

        invoice = Invoice(
            shop_id=shop.id,
            customer_id=customer_user.id,
            invoice_number="INV-DETAIL-001",
            total_amount=200.0,
            amount_paid=100.0,
            status=InvoiceStatus.PARTIALLY_PAID
        )
        session.add(invoice)
        session.commit()
        session.refresh(invoice)

        # Add items
        item = InvoiceItem(
            invoice_id=invoice.id,
            item_type="service",
            name="Brake Replacement",
            quantity=1.0,
            unit_price=200.0,
            total_price=200.0
        )
        session.add(item)

        # Add payment
        payment = Payment(
            invoice_id=invoice.id,
            amount=100.0,
            method=PaymentMethod.CASH
        )
        session.add(payment)
        session.commit()

        response = client.get(
            f"/api/v1/invoices/my-invoices/{invoice.id}",
            headers=customer_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["invoice_number"] == "INV-DETAIL-001"
        assert data["balance_due"] == 100.0
        assert len(data["items"]) == 1
        assert len(data["payments"]) == 1
