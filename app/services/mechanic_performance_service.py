"""Mechanic performance service for tracking and analytics."""
from datetime import datetime, date
from typing import Optional, List, Dict

from app.models.mechanic_performance import MechanicPerformance, MechanicRating
from app.repositories.mechanic_performance_repository import MechanicPerformanceRepository
from app.repositories.shop_repository import ShopRepository
from app.repositories.user_repository import UserRepository


class MechanicPerformanceService:
    def __init__(
        self,
        perf_repo: MechanicPerformanceRepository,
        shop_repo: ShopRepository,
        user_repo: UserRepository,
    ):
        self.perf_repo = perf_repo
        self.shop_repo = shop_repo
        self.user_repo = user_repo

    def record_performance(
        self,
        mechanic_id: int,
        shop_id: int,
        appointment_id: int,
        service_name: str,
        revenue_generated: float,
        estimated_duration: Optional[int] = None,
        actual_duration: Optional[int] = None,
    ) -> MechanicPerformance:
        return self.perf_repo.save_performance(
            MechanicPerformance(
                mechanic_id=mechanic_id,
                shop_id=shop_id,
                appointment_id=appointment_id,
                service_name=service_name,
                completed_date=datetime.utcnow(),
                revenue_generated=revenue_generated,
                estimated_duration=estimated_duration,
                actual_duration=actual_duration,
                is_completed=True,
            )
        )

    def add_customer_rating(
        self,
        mechanic_id: int,
        customer_id: int,
        appointment_id: int,
        rating: int,
        review: Optional[str] = None,
    ) -> MechanicRating:
        existing = self.perf_repo.get_mechanic_rating(appointment_id, customer_id)
        if existing:
            existing.rating = rating
            existing.review = review
            self.perf_repo.update_rating(existing)
            mechanic_rating = existing
        else:
            mechanic_rating = self.perf_repo.save_rating(
                MechanicRating(
                    mechanic_id=mechanic_id,
                    customer_id=customer_id,
                    appointment_id=appointment_id,
                    rating=rating,
                    review=review,
                )
            )

        performance = self.perf_repo.get_performance_by_appointment(appointment_id)
        if performance:
            performance.service_rating = rating
            performance.customer_feedback = review
            self.perf_repo.update_performance(performance)

        return mechanic_rating

    def get_mechanic_performance_summary(
        self,
        mechanic_id: int,
        shop_id: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Dict:
        performances = self.perf_repo.get_mechanic_performances(
            mechanic_id, shop_id, date_from, date_to
        )

        if not performances:
            return {
                "mechanic_id": mechanic_id,
                "total_jobs": 0,
                "total_revenue": 0.0,
                "average_rating": None,
                "efficiency_rate": None,
            }

        total_jobs = len(performances)
        total_revenue = sum(p.revenue_generated for p in performances)
        ratings = [p.service_rating for p in performances if p.service_rating]
        average_rating = sum(ratings) / len(ratings) if ratings else None

        efficiency_data = [
            (p.estimated_duration, p.actual_duration)
            for p in performances
            if p.estimated_duration and p.actual_duration
        ]
        if efficiency_data:
            total_estimated = sum(est for est, _ in efficiency_data)
            total_actual = sum(act for _, act in efficiency_data)
            efficiency_rate = (total_estimated / total_actual * 100) if total_actual > 0 else 100
        else:
            efficiency_rate = None

        mechanic = self.user_repo.get_by_id(mechanic_id)

        return {
            "mechanic_id": mechanic_id,
            "mechanic_name": mechanic.full_name if mechanic else "Unknown",
            "total_jobs": total_jobs,
            "total_revenue": total_revenue,
            "average_revenue_per_job": total_revenue / total_jobs,
            "average_rating": round(average_rating, 2) if average_rating else None,
            "efficiency_rate": round(efficiency_rate, 2) if efficiency_rate else None,
            "date_range": {
                "from": date_from.isoformat() if date_from else None,
                "to": date_to.isoformat() if date_to else None,
            },
        }

    def get_shop_mechanics_comparison(
        self,
        shop_id: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[Dict]:
        mechanics = self.shop_repo.get_active_members(shop_id)
        results = [
            self.get_mechanic_performance_summary(
                mechanic_id=m.user_id,
                shop_id=shop_id,
                date_from=date_from,
                date_to=date_to,
            )
            for m in mechanics
        ]
        results.sort(key=lambda x: x["total_revenue"], reverse=True)
        return results

    def get_mechanic_detailed_history(
        self, mechanic_id: int, shop_id: int, limit: int = 50
    ) -> List[MechanicPerformance]:
        return self.perf_repo.get_mechanic_history(mechanic_id, shop_id, limit)

    def get_shop_performance_summary(
        self,
        shop_id: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Dict:
        performances = self.perf_repo.get_shop_performances(shop_id, date_from, date_to)

        if not performances:
            return {
                "shop_id": shop_id,
                "total_jobs": 0,
                "total_revenue": 0.0,
                "mechanic_count": 0,
            }

        total_jobs = len(performances)
        total_revenue = sum(p.revenue_generated for p in performances)
        unique_mechanics = len(set(p.mechanic_id for p in performances))
        ratings = [p.service_rating for p in performances if p.service_rating]
        shop_average_rating = sum(ratings) / len(ratings) if ratings else None

        return {
            "shop_id": shop_id,
            "total_jobs": total_jobs,
            "total_revenue": total_revenue,
            "average_revenue_per_job": total_revenue / total_jobs,
            "mechanic_count": unique_mechanics,
            "shop_average_rating": round(shop_average_rating, 2) if shop_average_rating else None,
            "date_range": {
                "from": date_from.isoformat() if date_from else None,
                "to": date_to.isoformat() if date_to else None,
            },
        }

    def get_top_performing_mechanics(
        self,
        shop_id: int,
        limit: int = 5,
        metric: str = "revenue",
    ) -> List[Dict]:
        comparison = self.get_shop_mechanics_comparison(shop_id)
        if metric == "rating":
            comparison = [c for c in comparison if c["average_rating"]]
            comparison.sort(key=lambda x: x["average_rating"], reverse=True)
        elif metric == "jobs":
            comparison.sort(key=lambda x: x["total_jobs"], reverse=True)
        return comparison[:limit]
