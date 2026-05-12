from typing import Optional, List
from sqlmodel import Session, select

from app.models.product import Product, Service


class ProductRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_product(self, product_id: int) -> Optional[Product]:
        return self.session.get(Product, product_id)

    def get_service(self, service_id: int) -> Optional[Service]:
        return self.session.get(Service, service_id)

    def get_active_products_by_shop(self, shop_id: int) -> List[Product]:
        return self.session.exec(
            select(Product).where(
                Product.shop_id == shop_id,
                Product.is_active,
            )
        ).all()

    def get_active_services_by_shop(self, shop_id: int) -> List[Service]:
        return self.session.exec(
            select(Service).where(
                Service.shop_id == shop_id,
                Service.is_active,
            )
        ).all()

    def get_active_product_in_shop(
        self, product_id: int, shop_id: int
    ) -> Optional[Product]:
        return self.session.exec(
            select(Product).where(
                Product.id == product_id,
                Product.shop_id == shop_id,
                Product.is_active,
            )
        ).first()

    def decrease_stock(self, product: Product, quantity: int) -> None:
        product.stock_quantity -= quantity

    def increase_stock(self, product: Product, quantity: int) -> None:
        product.stock_quantity += quantity
