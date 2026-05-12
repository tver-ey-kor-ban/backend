"""Pricing service for calculating appointment and order totals."""
from typing import Optional, List, Dict

from app.models.product import ServiceType
from app.repositories.product_repository import ProductRepository
from app.repositories.order_repository import OrderRepository


class PricingService:
    def __init__(self, product_repo: ProductRepository, order_repo: OrderRepository):
        self.product_repo = product_repo
        self.order_repo = order_repo
        self.tax_rate = 0.0

    def calculate_appointment_price(
        self,
        service_id: Optional[int],
        product_items: Optional[List[Dict]] = None,
        discount_amount: float = 0.0,
    ) -> Dict:
        result = {
            "service_price": 0.0,
            "mobile_service_fee": 0.0,
            "products_total": 0.0,
            "subtotal": 0.0,
            "discount_amount": discount_amount,
            "tax_amount": 0.0,
            "total_amount": 0.0,
        }

        if service_id:
            service = self.product_repo.get_service(service_id)
            if service:
                result["service_price"] = service.price
                if service.service_type == ServiceType.MOBILE:
                    result["mobile_service_fee"] = service.mobile_service_fee or 0.0

        if product_items:
            for item in product_items:
                product = self.product_repo.get_product(item.get("product_id"))
                if product:
                    result["products_total"] += product.price * item.get("quantity", 1)

        result["subtotal"] = (
            result["service_price"]
            + result["mobile_service_fee"]
            + result["products_total"]
        )

        discounted_subtotal = max(result["subtotal"] - result["discount_amount"], 0.0)
        result["tax_amount"] = discounted_subtotal * self.tax_rate
        result["total_amount"] = discounted_subtotal + result["tax_amount"]

        return result

    def calculate_product_order_price(
        self,
        product_items: List[Dict],
        discount_amount: float = 0.0,
    ) -> Dict:
        result = {
            "products_total": 0.0,
            "discount_amount": discount_amount,
            "tax_amount": 0.0,
            "total_amount": 0.0,
        }

        for item in product_items:
            product = self.product_repo.get_product(item.get("product_id"))
            if product:
                result["products_total"] += product.price * item.get("quantity", 1)

        subtotal = max(result["products_total"] - result["discount_amount"], 0.0)
        result["tax_amount"] = subtotal * self.tax_rate
        result["total_amount"] = subtotal + result["tax_amount"]

        return result

    def get_price_breakdown(self, appointment_id: int) -> Optional[Dict]:
        appointment = self.order_repo.get_appointment(appointment_id)
        if not appointment:
            return None

        product_order = self.order_repo.get_order_by_shop_and_customer(
            appointment.shop_id, appointment.customer_id
        )

        breakdown = {
            "appointment_id": appointment.id,
            "service": {"name": None, "price": appointment.service_price},
            "mobile_fee": appointment.mobile_service_fee,
            "products": [],
            "products_total": 0.0,
            "subtotal": appointment.service_price + appointment.mobile_service_fee,
            "discount": appointment.discount_amount,
            "tax": appointment.tax_amount,
            "total": appointment.total_amount,
        }

        if appointment.service_id:
            service = self.product_repo.get_service(appointment.service_id)
            if service:
                breakdown["service"]["name"] = service.name

        if product_order:
            items = self.order_repo.get_order_items(product_order.id)
            for item in items:
                breakdown["products"].append({
                    "name": item.product_name,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total": item.total_price,
                })
                breakdown["products_total"] += item.total_price
            breakdown["subtotal"] += breakdown["products_total"]

        return breakdown
