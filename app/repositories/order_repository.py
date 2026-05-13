from typing import Optional, List
from sqlmodel import Session, select

from app.models.appointment import Appointment, AppointmentStatus
from app.models.product_order import ProductOrder, ProductOrderItem, OrderStatus


class OrderRepository:
    def __init__(self, session: Session):
        self.session = session

    # ── Appointments ──────────────────────────────────────────────────────────

    def get_appointment(self, appointment_id: int) -> Optional[Appointment]:
        return self.session.get(Appointment, appointment_id)

    def get_appointment_by_id_and_shop(
        self, appointment_id: int, shop_id: int
    ) -> Optional[Appointment]:
        return self.session.exec(
            select(Appointment).where(
                Appointment.id == appointment_id,
                Appointment.shop_id == shop_id,
            )
        ).first()

    def get_appointments_by_shop_and_status(
        self, shop_id: int, status: AppointmentStatus
    ) -> List[Appointment]:
        return self.session.exec(
            select(Appointment)
            .where(Appointment.shop_id == shop_id, Appointment.status == status)
            .order_by(Appointment.appointment_date.asc())
        ).all()

    def get_confirmed_appointments_in_range(
        self, shop_id: int, start: object, end: object
    ) -> List[Appointment]:
        return self.session.exec(
            select(Appointment)
            .where(
                Appointment.shop_id == shop_id,
                Appointment.status == AppointmentStatus.CONFIRMED,
                Appointment.appointment_date >= start,
                Appointment.appointment_date < end,
            )
            .order_by(Appointment.appointment_date.asc())
        ).all()

    def update_appointment(self, appointment: Appointment) -> None:
        self.session.commit()

    # ── Product orders ────────────────────────────────────────────────────────

    def get_order(self, order_id: int) -> Optional[ProductOrder]:
        return self.session.get(ProductOrder, order_id)

    def get_order_by_id_and_shop(
        self, order_id: int, shop_id: int
    ) -> Optional[ProductOrder]:
        return self.session.exec(
            select(ProductOrder).where(
                ProductOrder.id == order_id,
                ProductOrder.shop_id == shop_id,
            )
        ).first()

    def get_orders_by_shop_and_status(
        self, shop_id: int, status: OrderStatus
    ) -> List[ProductOrder]:
        return self.session.exec(
            select(ProductOrder)
            .where(ProductOrder.shop_id == shop_id, ProductOrder.status == status)
            .order_by(ProductOrder.created_at.desc())
        ).all()

    def get_order_by_shop_and_customer(
        self, shop_id: int, customer_id: int
    ) -> Optional[ProductOrder]:
        return self.session.exec(
            select(ProductOrder).where(
                ProductOrder.shop_id == shop_id,
                ProductOrder.customer_id == customer_id,
            )
        ).first()

    def update_order(self, order: ProductOrder) -> None:
        self.session.commit()

    def restore_order_stock(self, order_id: int) -> None:
        from app.models.product import Product

        items = self.get_order_items(order_id)
        for item in items:
            product = self.session.get(Product, item.product_id)
            if product:
                product.stock_quantity += item.quantity
        self.session.commit()

    # ── Order items ───────────────────────────────────────────────────────────

    def get_order_items(self, order_id: int) -> List[ProductOrderItem]:
        return self.session.exec(
            select(ProductOrderItem).where(ProductOrderItem.order_id == order_id)
        ).all()

    # ── Customer order views ──────────────────────────────────────────────────

    def get_orders_by_customer(
        self, customer_id: int, order_status: Optional[OrderStatus] = None
    ) -> List[ProductOrder]:
        query = (
            select(ProductOrder)
            .where(ProductOrder.customer_id == customer_id)
            .order_by(ProductOrder.created_at.desc())
        )
        if order_status:
            query = query.where(ProductOrder.status == order_status)
        return self.session.exec(query).all()

    def get_appointment_by_customer_and_id(
        self, appointment_id: int, customer_id: int
    ) -> Optional[Appointment]:
        return self.session.exec(
            select(Appointment).where(
                Appointment.id == appointment_id,
                Appointment.customer_id == customer_id,
            )
        ).first()

    def get_order_by_customer_and_id(
        self, order_id: int, customer_id: int
    ) -> Optional[ProductOrder]:
        return self.session.exec(
            select(ProductOrder).where(
                ProductOrder.id == order_id,
                ProductOrder.customer_id == customer_id,
            )
        ).first()

    def get_orders_by_shop_filtered(
        self, shop_id: int, order_status: Optional[OrderStatus] = None
    ) -> List[ProductOrder]:
        query = (
            select(ProductOrder)
            .where(ProductOrder.shop_id == shop_id)
            .order_by(ProductOrder.created_at.desc())
        )
        if order_status:
            query = query.where(ProductOrder.status == order_status)
        return self.session.exec(query).all()

    # ── Transaction helpers (multi-step operations) ───────────────────────────

    def add_pending(self, entity: object) -> None:
        """Stage an entity for insert without committing."""
        self.session.add(entity)

    def flush(self) -> None:
        """Flush pending operations to DB so auto-generated IDs are populated."""
        self.session.flush()

    def commit(self) -> None:
        self.session.commit()

    def refresh(self, entity: object) -> None:
        self.session.refresh(entity)
