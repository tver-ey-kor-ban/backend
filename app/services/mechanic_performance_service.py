"""Mechanic performance service for tracking and analytics."""
from datetime import datetime, date
from typing import Optional, List, Dict
from sqlmodel import Session, select

from app.models.mechanic_performance import MechanicPerformance, MechanicRating
from app.models.user import User
from app.models.shop import UserShop


class MechanicPerformanceService:
    """Service for tracking mechanic performance."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def record_performance(
        self,
        mechanic_id: int,
        shop_id: int,
        appointment_id: int,
        service_name: str,
        revenue_generated: float,
        estimated_duration: Optional[int] = None,
        actual_duration: Optional[int] = None
    ) -> MechanicPerformance:
        """Record a completed service performance."""
        performance = MechanicPerformance(
            mechanic_id=mechanic_id,
            shop_id=shop_id,
            appointment_id=appointment_id,
            service_name=service_name,
            completed_date=datetime.utcnow(),
            revenue_generated=revenue_generated,
            estimated_duration=estimated_duration,
            actual_duration=actual_duration,
            is_completed=True
        )
        self.session.add(performance)
        self.session.commit()
        self.session.refresh(performance)
        return performance
    
    def add_customer_rating(
        self,
        mechanic_id: int,
        customer_id: int,
        appointment_id: int,
        rating: int,
        review: Optional[str] = None
    ) -> MechanicRating:
        """Add customer rating for mechanic."""
        # Check if already rated
        existing = self.session.exec(
            select(MechanicRating).where(
                MechanicRating.appointment_id == appointment_id,
                MechanicRating.customer_id == customer_id
            )
        ).first()
        
        if existing:
            # Update existing rating
            existing.rating = rating
            existing.review = review
            self.session.commit()
            return existing
        
        new_rating = MechanicRating(
            mechanic_id=mechanic_id,
            customer_id=customer_id,
            appointment_id=appointment_id,
            rating=rating,
            review=review
        )
        self.session.add(new_rating)
        self.session.commit()
        self.session.refresh(new_rating)
        
        # Update performance record with rating
        performance = self.session.exec(
            select(MechanicPerformance).where(
                MechanicPerformance.appointment_id == appointment_id
            )
        ).first()
        
        if performance:
            performance.service_rating = rating
            performance.customer_feedback = review
            self.session.commit()
        
        return new_rating
    
    def get_mechanic_performance_summary(
        self,
        mechanic_id: int,
        shop_id: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> Dict:
        """Get performance summary for a single mechanic."""
        query = select(MechanicPerformance).where(
            MechanicPerformance.mechanic_id == mechanic_id,
            MechanicPerformance.shop_id == shop_id
        )
        
        if date_from:
            query = query.where(MechanicPerformance.completed_date >= date_from)
        if date_to:
            query = query.where(MechanicPerformance.completed_date <= date_to)
        
        performances = self.session.exec(query).all()
        
        if not performances:
            return {
                "mechanic_id": mechanic_id,
                "total_jobs": 0,
                "total_revenue": 0.0,
                "average_rating": None,
                "efficiency_rate": None
            }
        
        total_jobs = len(performances)
        total_revenue = sum(p.revenue_generated for p in performances)
        
        # Calculate average rating
        ratings = [p.service_rating for p in performances if p.service_rating]
        average_rating = sum(ratings) / len(ratings) if ratings else None
        
        # Calculate efficiency (actual vs estimated time)
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
        
        # Get mechanic info
        mechanic = self.session.get(User, mechanic_id)
        
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
                "to": date_to.isoformat() if date_to else None
            }
        }
    
    def get_shop_mechanics_comparison(
        self,
        shop_id: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> List[Dict]:
        """Compare all mechanics in a shop."""
        # Get all mechanics in shop
        mechanics = self.session.exec(
            select(UserShop).where(
                UserShop.shop_id == shop_id,
                UserShop.is_active
            )
        ).all()
        
        results = []
        for mechanic_shop in mechanics:
            summary = self.get_mechanic_performance_summary(
                mechanic_id=mechanic_shop.user_id,
                shop_id=shop_id,
                date_from=date_from,
                date_to=date_to
            )
            results.append(summary)
        
        # Sort by total revenue (descending)
        results.sort(key=lambda x: x["total_revenue"], reverse=True)
        
        return results
    
    def get_mechanic_detailed_history(
        self,
        mechanic_id: int,
        shop_id: int,
        limit: int = 50
    ) -> List[MechanicPerformance]:
        """Get detailed service history for a mechanic."""
        return self.session.exec(
            select(MechanicPerformance).where(
                MechanicPerformance.mechanic_id == mechanic_id,
                MechanicPerformance.shop_id == shop_id
            ).order_by(MechanicPerformance.completed_date.desc())
            .limit(limit)
        ).all()
    
    def get_shop_performance_summary(
        self,
        shop_id: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> Dict:
        """Get overall shop performance summary."""
        query = select(MechanicPerformance).where(
            MechanicPerformance.shop_id == shop_id
        )
        
        if date_from:
            query = query.where(MechanicPerformance.completed_date >= date_from)
        if date_to:
            query = query.where(MechanicPerformance.completed_date <= date_to)
        
        performances = self.session.exec(query).all()
        
        if not performances:
            return {
                "shop_id": shop_id,
                "total_jobs": 0,
                "total_revenue": 0.0,
                "mechanic_count": 0
            }
        
        total_jobs = len(performances)
        total_revenue = sum(p.revenue_generated for p in performances)
        
        # Count unique mechanics
        unique_mechanics = len(set(p.mechanic_id for p in performances))
        
        # Get all ratings
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
                "to": date_to.isoformat() if date_to else None
            }
        }
    
    def get_top_performing_mechanics(
        self,
        shop_id: int,
        limit: int = 5,
        metric: str = "revenue"  # "revenue", "rating", "jobs"
    ) -> List[Dict]:
        """Get top performing mechanics by metric."""
        comparison = self.get_shop_mechanics_comparison(shop_id)
        
        if metric == "rating":
            # Filter out mechanics with no ratings
            comparison = [c for c in comparison if c["average_rating"]]
            comparison.sort(key=lambda x: x["average_rating"], reverse=True)
        elif metric == "jobs":
            comparison.sort(key=lambda x: x["total_jobs"], reverse=True)
        # Default: revenue (already sorted)
        
        return comparison[:limit]
