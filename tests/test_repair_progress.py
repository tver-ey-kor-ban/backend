"""Tests for repair progress tracking endpoints."""
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.shop import Shop, UserShop, ShopRole
from app.models.appointment import Appointment, AppointmentStatus
from app.models.repair_progress import RepairProgress, RepairStage, RepairProgressUpdate


class TestRepairProgressCreation:
    """Test repair progress creation by shop."""

    def test_create_repair_progress(self, client: TestClient, session: Session, shop_owner, customer_user, owner_auth_headers):
        """Test shop owner creating repair progress."""
        shop = Shop(name="Repair Shop", address="123 St")
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

        response = client.post(
            f"/api/v1/repair-progress/shops/{shop.id}",
            json={
                "shop_id": shop.id,
                "appointment_id": appointment.id,
                "stage": "received",
                "description": "Vehicle received for inspection",
                "estimated_completion": (datetime.utcnow() + timedelta(days=3)).isoformat()
            },
            headers=owner_auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["stage"] == RepairStage.RECEIVED
        assert data["appointment_id"] == appointment.id

    def test_duplicate_progress_not_allowed(self, client: TestClient, session: Session, shop_owner, customer_user, owner_auth_headers):
        """Test cannot create duplicate progress for same appointment."""
        shop = Shop(name="Repair Shop 2", address="123 St")
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

        # Create first progress
        progress = RepairProgress(
            shop_id=shop.id,
            customer_id=customer_user.id,
            appointment_id=appointment.id,
            stage=RepairStage.RECEIVED
        )
        session.add(progress)
        session.commit()

        # Try to create second
        response = client.post(
            f"/api/v1/repair-progress/shops/{shop.id}",
            json={
                "shop_id": shop.id,
                "appointment_id": appointment.id,
                "stage": "received"
            },
            headers=owner_auth_headers
        )
        assert response.status_code == 400


class TestRepairProgressUpdates:
    """Test updating repair progress stages."""

    def test_update_repair_stage(self, client: TestClient, session: Session, shop_owner, customer_user, owner_auth_headers):
        """Test updating repair stage."""
        shop = Shop(name="Update Shop", address="123 St")
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

        progress = RepairProgress(
            shop_id=shop.id,
            customer_id=customer_user.id,
            appointment_id=appointment.id,
            stage=RepairStage.RECEIVED
        )
        session.add(progress)
        session.commit()
        session.refresh(progress)

        response = client.put(
            f"/api/v1/repair-progress/shops/{shop.id}/{progress.id}",
            json={
                "stage": "in_progress",
                "note": "Started engine repair"
            },
            headers=owner_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["new_stage"] == "in_progress"
        assert data["previous_stage"] == "received"

    def test_complete_repair_updates_appointment(self, client: TestClient, session: Session, shop_owner, customer_user, owner_auth_headers):
        """Test completing repair updates appointment status."""
        shop = Shop(name="Complete Shop", address="123 St")
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

        progress = RepairProgress(
            shop_id=shop.id,
            customer_id=customer_user.id,
            appointment_id=appointment.id,
            stage=RepairStage.IN_PROGRESS
        )
        session.add(progress)
        session.commit()
        session.refresh(progress)

        response = client.put(
            f"/api/v1/repair-progress/shops/{shop.id}/{progress.id}",
            json={
                "stage": "completed",
                "note": "Repair finished"
            },
            headers=owner_auth_headers
        )
        assert response.status_code == 200

        # Verify appointment status updated
        session.refresh(appointment)
        assert appointment.status == AppointmentStatus.COMPLETED


class TestCustomerRepairView:
    """Test customer viewing repair progress."""

    def test_customer_view_repairs(self, client: TestClient, session: Session, shop_owner, customer_user, customer_auth_headers):
        """Test customer viewing their repair progress."""
        shop = Shop(name="Cust Repair Shop", address="123 St")
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

        progress = RepairProgress(
            shop_id=shop.id,
            customer_id=customer_user.id,
            appointment_id=appointment.id,
            stage=RepairStage.DIAGNOSING,
            description="Checking engine"
        )
        session.add(progress)
        session.commit()

        response = client.get(
            "/api/v1/repair-progress/my-repairs",
            headers=customer_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["stage"] == "diagnosing"

    def test_customer_view_repair_detail(self, client: TestClient, session: Session, shop_owner, customer_user, customer_auth_headers):
        """Test customer viewing repair detail with updates."""
        shop = Shop(name="Detail Shop", address="123 St")
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

        progress = RepairProgress(
            shop_id=shop.id,
            customer_id=customer_user.id,
            appointment_id=appointment.id,
            stage=RepairStage.IN_PROGRESS
        )
        session.add(progress)
        session.commit()
        session.refresh(progress)

        # Add some updates
        update1 = RepairProgressUpdate(
            repair_progress_id=progress.id,
            updated_by=shop_owner.id,
            from_stage="received",
            to_stage="diagnosing",
            note="Found issue"
        )
        update2 = RepairProgressUpdate(
            repair_progress_id=progress.id,
            updated_by=shop_owner.id,
            from_stage="diagnosing",
            to_stage="in_progress",
            note="Started repair"
        )
        session.add(update1)
        session.add(update2)
        session.commit()

        response = client.get(
            f"/api/v1/repair-progress/my-repairs/{progress.id}",
            headers=customer_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["stage"] == "in_progress"
        assert len(data["updates"]) == 2
