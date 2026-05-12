from datetime import datetime
from typing import Optional, List
from sqlmodel import Session, select

from app.models.ratings import ProductRating, ServiceRating


class RatingRepository:
    def __init__(self, session: Session):
        self.session = session

    # ── Product ratings ──────────────────────────────────────────────────────

    def get_product_rating(
        self,
        product_id: int,
        customer_id: int,
        order_id: Optional[int],
    ) -> Optional[ProductRating]:
        return self.session.exec(
            select(ProductRating).where(
                ProductRating.product_id == product_id,
                ProductRating.customer_id == customer_id,
                ProductRating.order_id == order_id,
            )
        ).first()

    def save_product_rating(self, rating: ProductRating) -> ProductRating:
        self.session.add(rating)
        self.session.commit()
        self.session.refresh(rating)
        return rating

    def update_product_rating(
        self, rating: ProductRating, new_rating: int, review: Optional[str]
    ) -> ProductRating:
        rating.rating = new_rating
        rating.review = review
        rating.updated_at = datetime.utcnow()
        self.session.commit()
        return rating

    def get_product_ratings(self, product_id: int) -> List[ProductRating]:
        return self.session.exec(
            select(ProductRating).where(ProductRating.product_id == product_id)
        ).all()

    def get_product_reviews(self, product_id: int, limit: int = 20) -> List[ProductRating]:
        return self.session.exec(
            select(ProductRating)
            .where(ProductRating.product_id == product_id)
            .order_by(ProductRating.created_at.desc())
            .limit(limit)
        ).all()

    # ── Service ratings ──────────────────────────────────────────────────────

    def get_service_rating(
        self,
        service_id: int,
        customer_id: int,
        appointment_id: Optional[int],
    ) -> Optional[ServiceRating]:
        return self.session.exec(
            select(ServiceRating).where(
                ServiceRating.service_id == service_id,
                ServiceRating.customer_id == customer_id,
                ServiceRating.appointment_id == appointment_id,
            )
        ).first()

    def save_service_rating(self, rating: ServiceRating) -> ServiceRating:
        self.session.add(rating)
        self.session.commit()
        self.session.refresh(rating)
        return rating

    def update_service_rating(
        self, rating: ServiceRating, new_rating: int, review: Optional[str]
    ) -> ServiceRating:
        rating.rating = new_rating
        rating.review = review
        rating.updated_at = datetime.utcnow()
        self.session.commit()
        return rating

    def get_service_ratings(self, service_id: int) -> List[ServiceRating]:
        return self.session.exec(
            select(ServiceRating).where(ServiceRating.service_id == service_id)
        ).all()

    def get_service_reviews(self, service_id: int, limit: int = 20) -> List[ServiceRating]:
        return self.session.exec(
            select(ServiceRating)
            .where(ServiceRating.service_id == service_id)
            .order_by(ServiceRating.created_at.desc())
            .limit(limit)
        ).all()

    def get_product_ratings_by_customer(self, customer_id: int) -> List[ProductRating]:
        return self.session.exec(
            select(ProductRating)
            .where(ProductRating.customer_id == customer_id)
            .order_by(ProductRating.created_at.desc())
        ).all()

    def get_service_ratings_by_customer(self, customer_id: int) -> List[ServiceRating]:
        return self.session.exec(
            select(ServiceRating)
            .where(ServiceRating.customer_id == customer_id)
            .order_by(ServiceRating.created_at.desc())
        ).all()
