"""Rating service for products and services."""
from datetime import datetime
from typing import Optional, List, Dict
from sqlmodel import Session, select

from app.models.ratings import ProductRating, ServiceRating, RatingSummary
from app.models.product import Product, Service
from app.models.product_order import ProductOrder, OrderStatus
from app.models.appointment import Appointment, AppointmentStatus


class RatingService:
    """Service for handling product and service ratings."""
    
    def __init__(self, session: Session):
        self.session = session
    
    # ==================== PRODUCT RATINGS ====================
    
    def rate_product(
        self,
        customer_id: int,
        product_id: int,
        rating: int,
        review: Optional[str] = None,
        order_id: Optional[int] = None
    ) -> ProductRating:
        """Rate a product."""
        # Verify customer bought this product (if order_id provided)
        if order_id:
            order = self.session.get(ProductOrder, order_id)
            if not order or order.customer_id != customer_id:
                raise ValueError("Invalid order")
            if order.status not in [OrderStatus.COMPLETED, OrderStatus.READY]:
                raise ValueError("Can only rate after order is completed")
        
        # Check if already rated
        existing = self.session.exec(
            select(ProductRating).where(
                ProductRating.product_id == product_id,
                ProductRating.customer_id == customer_id,
                ProductRating.order_id == order_id
            )
        ).first()
        
        if existing:
            # Update existing
            existing.rating = rating
            existing.review = review
            existing.updated_at = datetime.utcnow()
            self.session.commit()
            return existing
        
        # Create new rating
        new_rating = ProductRating(
            product_id=product_id,
            customer_id=customer_id,
            order_id=order_id,
            rating=rating,
            review=review
        )
        self.session.add(new_rating)
        self.session.commit()
        self.session.refresh(new_rating)
        
        return new_rating
    
    def get_product_rating_summary(self, product_id: int) -> RatingSummary:
        """Get rating summary for a product."""
        ratings = self.session.exec(
            select(ProductRating).where(ProductRating.product_id == product_id)
        ).all()
        
        if not ratings:
            return RatingSummary(
                average_rating=0.0,
                total_ratings=0,
                five_star=0, four_star=0, three_star=0, two_star=0, one_star=0
            )
        
        total = len(ratings)
        stars = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
        for r in ratings:
            stars[r.rating] = stars.get(r.rating, 0) + 1
        
        avg = sum(r.rating for r in ratings) / total
        
        return RatingSummary(
            average_rating=round(avg, 2),
            total_ratings=total,
            five_star=stars[5],
            four_star=stars[4],
            three_star=stars[3],
            two_star=stars[2],
            one_star=stars[1]
        )
    
    def get_product_reviews(self, product_id: int, limit: int = 20) -> List[ProductRating]:
        """Get reviews for a product."""
        return self.session.exec(
            select(ProductRating).where(
                ProductRating.product_id == product_id
            ).order_by(ProductRating.created_at.desc())
            .limit(limit)
        ).all()
    
    # ==================== SERVICE RATINGS ====================
    
    def rate_service(
        self,
        customer_id: int,
        service_id: int,
        rating: int,
        review: Optional[str] = None,
        appointment_id: Optional[int] = None
    ) -> ServiceRating:
        """Rate a service."""
        # Verify customer had this service (if appointment_id provided)
        if appointment_id:
            appointment = self.session.get(Appointment, appointment_id)
            if not appointment or appointment.customer_id != customer_id:
                raise ValueError("Invalid appointment")
            if appointment.status != AppointmentStatus.COMPLETED:
                raise ValueError("Can only rate after service is completed")
        
        # Check if already rated
        existing = self.session.exec(
            select(ServiceRating).where(
                ServiceRating.service_id == service_id,
                ServiceRating.customer_id == customer_id,
                ServiceRating.appointment_id == appointment_id
            )
        ).first()
        
        if existing:
            # Update existing
            existing.rating = rating
            existing.review = review
            existing.updated_at = datetime.utcnow()
            self.session.commit()
            return existing
        
        # Create new rating
        new_rating = ServiceRating(
            service_id=service_id,
            customer_id=customer_id,
            appointment_id=appointment_id,
            rating=rating,
            review=review
        )
        self.session.add(new_rating)
        self.session.commit()
        self.session.refresh(new_rating)
        
        return new_rating
    
    def get_service_rating_summary(self, service_id: int) -> RatingSummary:
        """Get rating summary for a service."""
        ratings = self.session.exec(
            select(ServiceRating).where(ServiceRating.service_id == service_id)
        ).all()
        
        if not ratings:
            return RatingSummary(
                average_rating=0.0,
                total_ratings=0,
                five_star=0, four_star=0, three_star=0, two_star=0, one_star=0
            )
        
        total = len(ratings)
        stars = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
        for r in ratings:
            stars[r.rating] = stars.get(r.rating, 0) + 1
        
        avg = sum(r.rating for r in ratings) / total
        
        return RatingSummary(
            average_rating=round(avg, 2),
            total_ratings=total,
            five_star=stars[5],
            four_star=stars[4],
            three_star=stars[3],
            two_star=stars[2],
            one_star=stars[1]
        )
    
    def get_service_reviews(self, service_id: int, limit: int = 20) -> List[ServiceRating]:
        """Get reviews for a service."""
        return self.session.exec(
            select(ServiceRating).where(
                ServiceRating.service_id == service_id
            ).order_by(ServiceRating.created_at.desc())
            .limit(limit)
        ).all()
    
    # ==================== SHOP-WIDE RATINGS ====================
    
    def get_shop_top_rated_products(self, shop_id: int, limit: int = 10) -> List[Dict]:
        """Get top rated products in a shop."""
        products = self.session.exec(
            select(Product).where(
                Product.shop_id == shop_id,
                Product.is_active
            )
        ).all()
        
        results = []
        for product in products:
            summary = self.get_product_rating_summary(product.id)
            if summary.total_ratings > 0:
                results.append({
                    "product_id": product.id,
                    "name": product.name,
                    "average_rating": summary.average_rating,
                    "total_ratings": summary.total_ratings
                })
        
        # Sort by rating
        results.sort(key=lambda x: x["average_rating"], reverse=True)
        return results[:limit]
    
    def get_shop_top_rated_services(self, shop_id: int, limit: int = 10) -> List[Dict]:
        """Get top rated services in a shop."""
        services = self.session.exec(
            select(Service).where(
                Service.shop_id == shop_id,
                Service.is_active 
            )
        ).all()
        
        results = []
        for service in services:
            summary = self.get_service_rating_summary(service.id)
            if summary.total_ratings > 0:
                results.append({
                    "service_id": service.id,
                    "name": service.name,
                    "average_rating": summary.average_rating,
                    "total_ratings": summary.total_ratings
                })
        
        # Sort by rating
        results.sort(key=lambda x: x["average_rating"], reverse=True)
        return results[:limit]
