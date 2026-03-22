"""Pricing service for calculating appointment and order totals."""
from typing import Optional, List, Dict
from sqlmodel import Session, select

from app.models.product import Service, ServiceType
from app.models.product_order import ProductOrderItem


class PricingService:
    """Service for calculating prices for appointments and orders."""
    
    def __init__(self, session: Session):
        self.session = session
        self.tax_rate = 0.0  # Configure tax rate (e.g., 0.10 for 10%)
    
    def calculate_appointment_price(
        self,
        service_id: Optional[int],
        product_items: Optional[List[Dict]] = None,
        discount_amount: float = 0.0
    ) -> Dict:
        """Calculate total price for appointment with optional products.
        
        Returns:
            {
                "service_price": float,
                "mobile_service_fee": float,
                "products_total": float,
                "subtotal": float,
                "discount_amount": float,
                "tax_amount": float,
                "total_amount": float
            }
        """
        result = {
            "service_price": 0.0,
            "mobile_service_fee": 0.0,
            "products_total": 0.0,
            "subtotal": 0.0,
            "discount_amount": discount_amount,
            "tax_amount": 0.0,
            "total_amount": 0.0
        }
        
        # Calculate service price
        if service_id:
            service = self.session.get(Service, service_id)
            if service:
                result["service_price"] = service.price
                
                # Add mobile service fee if applicable
                if service.service_type == ServiceType.MOBILE:
                    result["mobile_service_fee"] = service.mobile_service_fee or 0.0
        
        # Calculate products total
        if product_items:
            for item in product_items:
                product_id = item.get("product_id")
                quantity = item.get("quantity", 1)
                
                from app.models.product import Product
                product = self.session.get(Product, product_id)
                if product:
                    result["products_total"] += product.price * quantity
        
        # Calculate subtotal
        result["subtotal"] = (
            result["service_price"] +
            result["mobile_service_fee"] +
            result["products_total"]
        )
        
        # Apply discount
        discounted_subtotal = result["subtotal"] - result["discount_amount"]
        if discounted_subtotal < 0:
            discounted_subtotal = 0.0
        
        # Calculate tax
        result["tax_amount"] = discounted_subtotal * self.tax_rate
        
        # Calculate total
        result["total_amount"] = discounted_subtotal + result["tax_amount"]
        
        return result
    
    def calculate_product_order_price(
        self,
        product_items: List[Dict],
        discount_amount: float = 0.0
    ) -> Dict:
        """Calculate total price for product order only.
        
        Returns:
            {
                "products_total": float,
                "discount_amount": float,
                "tax_amount": float,
                "total_amount": float
            }
        """
        result = {
            "products_total": 0.0,
            "discount_amount": discount_amount,
            "tax_amount": 0.0,
            "total_amount": 0.0
        }
        
        # Calculate products total
        for item in product_items:
            product_id = item.get("product_id")
            quantity = item.get("quantity", 1)
            
            from app.models.product import Product
            product = self.session.get(Product, product_id)
            if product:
                result["products_total"] += product.price * quantity
        
        # Apply discount
        subtotal = result["products_total"] - result["discount_amount"]
        if subtotal < 0:
            subtotal = 0.0
        
        # Calculate tax
        result["tax_amount"] = subtotal * self.tax_rate
        
        # Calculate total
        result["total_amount"] = subtotal + result["tax_amount"]
        
        return result
    
    def get_price_breakdown(self, appointment_id: int) -> Optional[Dict]:
        """Get detailed price breakdown for an appointment."""
        from app.models.appointment import Appointment
        
        appointment = self.session.get(Appointment, appointment_id)
        if not appointment:
            return None
        
        # Get product order if exists
        from app.models.product_order import ProductOrder
        product_order = self.session.exec(
            select(ProductOrder).where(
                ProductOrder.shop_id == appointment.shop_id,
                ProductOrder.customer_id == appointment.customer_id
            )
        ).first()
        
        breakdown = {
            "appointment_id": appointment.id,
            "service": {
                "name": None,
                "price": appointment.service_price
            },
            "mobile_fee": appointment.mobile_service_fee,
            "products": [],
            "products_total": 0.0,
            "subtotal": appointment.service_price + appointment.mobile_service_fee,
            "discount": appointment.discount_amount,
            "tax": appointment.tax_amount,
            "total": appointment.total_amount
        }
        
        # Get service name
        if appointment.service_id:
            service = self.session.get(Service, appointment.service_id)
            if service:
                breakdown["service"]["name"] = service.name
        
        # Get products from order
        if product_order:
            items = self.session.exec(
                select(ProductOrderItem).where(
                    ProductOrderItem.order_id == product_order.id
                )
            ).all()
            
            for item in items:
                breakdown["products"].append({
                    "name": item.product_name,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total": item.total_price
                })
                breakdown["products_total"] += item.total_price
            
            breakdown["subtotal"] += breakdown["products_total"]
        
        return breakdown
