from datetime import date
from typing import Optional, List
from sqlmodel import Session, select

from app.models.mechanic_performance import MechanicPerformance, MechanicRating


class MechanicPerformanceRepository:
    def __init__(self, session: Session):
        self.session = session

    def save_performance(self, performance: MechanicPerformance) -> MechanicPerformance:
        self.session.add(performance)
        self.session.commit()
        self.session.refresh(performance)
        return performance

    def get_performance_by_appointment(
        self, appointment_id: int
    ) -> Optional[MechanicPerformance]:
        return self.session.exec(
            select(MechanicPerformance).where(
                MechanicPerformance.appointment_id == appointment_id
            )
        ).first()

    def update_performance(self, performance: MechanicPerformance) -> None:
        self.session.commit()

    def get_mechanic_performances(
        self,
        mechanic_id: int,
        shop_id: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[MechanicPerformance]:
        query = select(MechanicPerformance).where(
            MechanicPerformance.mechanic_id == mechanic_id,
            MechanicPerformance.shop_id == shop_id,
        )
        if date_from:
            query = query.where(MechanicPerformance.completed_date >= date_from)
        if date_to:
            query = query.where(MechanicPerformance.completed_date <= date_to)
        return self.session.exec(query).all()

    def get_shop_performances(
        self,
        shop_id: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[MechanicPerformance]:
        query = select(MechanicPerformance).where(
            MechanicPerformance.shop_id == shop_id
        )
        if date_from:
            query = query.where(MechanicPerformance.completed_date >= date_from)
        if date_to:
            query = query.where(MechanicPerformance.completed_date <= date_to)
        return self.session.exec(query).all()

    def get_mechanic_history(
        self, mechanic_id: int, shop_id: int, limit: int = 50
    ) -> List[MechanicPerformance]:
        return self.session.exec(
            select(MechanicPerformance)
            .where(
                MechanicPerformance.mechanic_id == mechanic_id,
                MechanicPerformance.shop_id == shop_id,
            )
            .order_by(MechanicPerformance.completed_date.desc())
            .limit(limit)
        ).all()

    def get_mechanic_rating(
        self, appointment_id: int, customer_id: int
    ) -> Optional[MechanicRating]:
        return self.session.exec(
            select(MechanicRating).where(
                MechanicRating.appointment_id == appointment_id,
                MechanicRating.customer_id == customer_id,
            )
        ).first()

    def save_rating(self, rating: MechanicRating) -> MechanicRating:
        self.session.add(rating)
        self.session.commit()
        self.session.refresh(rating)
        return rating

    def update_rating(self, rating: MechanicRating) -> None:
        self.session.commit()

    def get_mechanic_history_paginated(
        self, mechanic_id: int, shop_id: int, offset: int, limit: int
    ) -> List[MechanicPerformance]:
        return self.session.exec(
            select(MechanicPerformance)
            .where(
                MechanicPerformance.mechanic_id == mechanic_id,
                MechanicPerformance.shop_id == shop_id,
            )
            .order_by(MechanicPerformance.completed_date.desc())
            .offset(offset)
            .limit(limit)
        ).all()

    def count_mechanic_history(self, mechanic_id: int, shop_id: int) -> int:
        return len(
            self.session.exec(
                select(MechanicPerformance).where(
                    MechanicPerformance.mechanic_id == mechanic_id,
                    MechanicPerformance.shop_id == shop_id,
                )
            ).all()
        )
