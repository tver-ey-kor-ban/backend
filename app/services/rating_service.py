"""Rating service for products and services."""
from typing import Optional, List, Dict

from app.models.ratings import ProductRating, ServiceRating, RatingSummary
from app.models.product_order import OrderStatus
from app.models.appointment import AppointmentStatus
from app.repositories.rating_repository import RatingRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository


class RatingService:
    def __init__(
        self,
        rating_repo: RatingRepository,
        order_repo: OrderRepository,
        product_repo: ProductRepository,
    ):
        self.rating_repo = rating_repo
        self.order_repo = order_repo
        self.product_repo = product_repo

    # ── Product ratings ───────────────────────────────────────────────────────

    def rate_product(
        self,
        customer_id: int,
        product_id: int,
        rating: int,
        review: Optional[str] = None,
        order_id: Optional[int] = None,
    ) -> ProductRating:
        if order_id:
            order = self.order_repo.get_order(order_id)
            if not order or order.customer_id != customer_id:
                raise ValueError("Invalid order")
            if order.status not in [OrderStatus.COMPLETED, OrderStatus.READY]:
                raise ValueError("Can only rate after order is completed")

        existing = self.rating_repo.get_product_rating(product_id, customer_id, order_id)
        if existing:
            return self.rating_repo.update_product_rating(existing, rating, review)

        return self.rating_repo.save_product_rating(
            ProductRating(
                product_id=product_id,
                customer_id=customer_id,
                order_id=order_id,
                rating=rating,
                review=review,
            )
        )

    def get_product_rating_summary(self, product_id: int) -> RatingSummary:
        ratings = self.rating_repo.get_product_ratings(product_id)
        return self._build_summary(ratings)

    def get_product_reviews(self, product_id: int, limit: int = 20) -> List[ProductRating]:
        return self.rating_repo.get_product_reviews(product_id, limit)

    # ── Service ratings ───────────────────────────────────────────────────────

    def rate_service(
        self,
        customer_id: int,
        service_id: int,
        rating: int,
        review: Optional[str] = None,
        appointment_id: Optional[int] = None,
    ) -> ServiceRating:
        if appointment_id:
            appointment = self.order_repo.get_appointment(appointment_id)
            if not appointment or appointment.customer_id != customer_id:
                raise ValueError("Invalid appointment")
            if appointment.status != AppointmentStatus.COMPLETED:
                raise ValueError("Can only rate after service is completed")

        existing = self.rating_repo.get_service_rating(service_id, customer_id, appointment_id)
        if existing:
            return self.rating_repo.update_service_rating(existing, rating, review)

        return self.rating_repo.save_service_rating(
            ServiceRating(
                service_id=service_id,
                customer_id=customer_id,
                appointment_id=appointment_id,
                rating=rating,
                review=review,
            )
        )

    def get_service_rating_summary(self, service_id: int) -> RatingSummary:
        ratings = self.rating_repo.get_service_ratings(service_id)
        return self._build_summary(ratings)

    def get_service_reviews(self, service_id: int, limit: int = 20) -> List[ServiceRating]:
        return self.rating_repo.get_service_reviews(service_id, limit)

    # ── Shop-wide ratings ─────────────────────────────────────────────────────

    def get_shop_top_rated_products(self, shop_id: int, limit: int = 10) -> List[Dict]:
        products = self.product_repo.get_active_products_by_shop(shop_id)
        results = []
        for product in products:
            summary = self.get_product_rating_summary(product.id)
            if summary.total_ratings > 0:
                results.append({
                    "product_id": product.id,
                    "name": product.name,
                    "average_rating": summary.average_rating,
                    "total_ratings": summary.total_ratings,
                })
        results.sort(key=lambda x: x["average_rating"], reverse=True)
        return results[:limit]

    def get_shop_top_rated_services(self, shop_id: int, limit: int = 10) -> List[Dict]:
        services = self.product_repo.get_active_services_by_shop(shop_id)
        results = []
        for service in services:
            summary = self.get_service_rating_summary(service.id)
            if summary.total_ratings > 0:
                results.append({
                    "service_id": service.id,
                    "name": service.name,
                    "average_rating": summary.average_rating,
                    "total_ratings": summary.total_ratings,
                })
        results.sort(key=lambda x: x["average_rating"], reverse=True)
        return results[:limit]

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _build_summary(ratings) -> RatingSummary:
        if not ratings:
            return RatingSummary(
                average_rating=0.0,
                total_ratings=0,
                five_star=0, four_star=0, three_star=0, two_star=0, one_star=0,
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
            one_star=stars[1],
        )
