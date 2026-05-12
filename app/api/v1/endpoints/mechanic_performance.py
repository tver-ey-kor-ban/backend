"""Mechanic performance endpoints for shop owners."""
from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session

from app.db import get_session
from app.core.security import get_current_user, TokenData
from app.repositories.shop_repository import ShopRepository
from app.repositories.user_repository import UserRepository
from app.repositories.mechanic_performance_repository import MechanicPerformanceRepository
from app.repositories.order_repository import OrderRepository
from app.services.shop_service import ShopService
from app.services.mechanic_performance_service import MechanicPerformanceService
from app.models.mechanic_performance import (
    MechanicPerformanceCreate,
    MechanicRatingCreate,
)
from app.models.appointment import AppointmentStatus

router = APIRouter(prefix="/shops/{shop_id}/mechanics", tags=["mechanic-performance"])


def get_shop_service(session: Session = Depends(get_session)) -> ShopService:
    return ShopService(ShopRepository(session))


def get_perf_service(session: Session = Depends(get_session)) -> MechanicPerformanceService:
    return MechanicPerformanceService(
        MechanicPerformanceRepository(session),
        ShopRepository(session),
        UserRepository(session),
    )


def get_perf_repo(session: Session = Depends(get_session)) -> MechanicPerformanceRepository:
    return MechanicPerformanceRepository(session)


def get_order_repo(session: Session = Depends(get_session)) -> OrderRepository:
    return OrderRepository(session)


# ── Owner: all mechanics performance ─────────────────────────────────────────

@router.get("/performance")
def get_all_mechanics_performance(
    shop_id: int,
    date_from: Optional[date] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    current_user: TokenData = Depends(get_current_user),
    shop_service: ShopService = Depends(get_shop_service),
    perf_service: MechanicPerformanceService = Depends(get_perf_service),
):
    """Get performance comparison for all mechanics in shop (Owner only)."""
    if not shop_service.is_shop_owner(current_user.user_id, shop_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only shop owner can view mechanic performance")

    if not date_from:
        date_from = date.today() - timedelta(days=30)
    if not date_to:
        date_to = date.today()

    comparison = perf_service.get_shop_mechanics_comparison(shop_id, date_from, date_to)
    shop_summary = perf_service.get_shop_performance_summary(shop_id, date_from, date_to)

    return {
        "shop_summary": shop_summary,
        "mechanics": comparison,
        "total_mechanics": len(comparison),
    }


@router.get("/performance/top")
def get_top_mechanics(
    shop_id: int,
    metric: str = Query("revenue", description="Sort by: revenue, rating, jobs"),
    limit: int = Query(5, ge=1, le=20),
    current_user: TokenData = Depends(get_current_user),
    shop_service: ShopService = Depends(get_shop_service),
    perf_service: MechanicPerformanceService = Depends(get_perf_service),
):
    """Get top performing mechanics (Owner only)."""
    if not shop_service.is_shop_owner(current_user.user_id, shop_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only shop owner can view mechanic performance")

    top_mechanics = perf_service.get_top_performing_mechanics(shop_id, limit, metric)
    return {"metric": metric, "top_mechanics": top_mechanics}


# ── Owner: individual mechanic performance ────────────────────────────────────

@router.get("/{mechanic_id}/performance")
def get_mechanic_performance(
    shop_id: int,
    mechanic_id: int,
    date_from: Optional[date] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    current_user: TokenData = Depends(get_current_user),
    shop_service: ShopService = Depends(get_shop_service),
    perf_service: MechanicPerformanceService = Depends(get_perf_service),
):
    """Get detailed performance for specific mechanic (Owner or the mechanic themselves)."""
    is_owner = shop_service.is_shop_owner(current_user.user_id, shop_id)
    is_self = current_user.user_id == mechanic_id

    if not (is_owner or is_self):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner or the mechanic can view this performance")

    if not shop_service.is_shop_member(mechanic_id, shop_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mechanic not found in this shop")

    if not date_from:
        date_from = date.today() - timedelta(days=30)
    if not date_to:
        date_to = date.today()

    summary = perf_service.get_mechanic_performance_summary(mechanic_id, shop_id, date_from, date_to)
    history = perf_service.get_mechanic_detailed_history(mechanic_id, shop_id, limit=20)

    return {
        "summary": summary,
        "recent_jobs": [
            {
                "id": h.id,
                "service_name": h.service_name,
                "completed_date": h.completed_date,
                "revenue_generated": h.revenue_generated,
                "service_rating": h.service_rating,
                "estimated_duration": h.estimated_duration,
                "actual_duration": h.actual_duration,
            }
            for h in history
        ],
    }


@router.get("/{mechanic_id}/performance/history")
def get_mechanic_full_history(
    shop_id: int,
    mechanic_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: TokenData = Depends(get_current_user),
    shop_service: ShopService = Depends(get_shop_service),
    perf_repo: MechanicPerformanceRepository = Depends(get_perf_repo),
):
    """Get full service history for a mechanic with pagination (Owner only)."""
    if not shop_service.is_shop_owner(current_user.user_id, shop_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only shop owner can view full mechanic history")

    offset = (page - 1) * page_size
    history = perf_repo.get_mechanic_history_paginated(mechanic_id, shop_id, offset, page_size)
    total_count = perf_repo.count_mechanic_history(mechanic_id, shop_id)

    return {
        "page": page,
        "page_size": page_size,
        "total_count": total_count,
        "total_pages": (total_count + page_size - 1) // page_size,
        "history": history,
    }


# ── Record performance ────────────────────────────────────────────────────────

@router.post("/{mechanic_id}/performance/record")
def record_mechanic_performance(
    shop_id: int,
    mechanic_id: int,
    performance_data: MechanicPerformanceCreate,
    current_user: TokenData = Depends(get_current_user),
    shop_service: ShopService = Depends(get_shop_service),
    perf_service: MechanicPerformanceService = Depends(get_perf_service),
):
    """Record mechanic performance for completed service (Owner only)."""
    if not shop_service.is_shop_owner(current_user.user_id, shop_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only shop owner can record performance")

    performance = perf_service.record_performance(
        mechanic_id=mechanic_id,
        shop_id=shop_id,
        appointment_id=performance_data.appointment_id,
        service_name=performance_data.service_name,
        revenue_generated=performance_data.revenue_generated,
        estimated_duration=performance_data.estimated_duration,
        actual_duration=performance_data.actual_duration,
    )
    return {"message": "Performance recorded successfully", "performance_id": performance.id}


# ── Customer rates mechanic ───────────────────────────────────────────────────

@router.post("/{mechanic_id}/rate")
def rate_mechanic(
    shop_id: int,
    mechanic_id: int,
    rating_data: MechanicRatingCreate,
    current_user: TokenData = Depends(get_current_user),
    perf_service: MechanicPerformanceService = Depends(get_perf_service),
    order_repo: OrderRepository = Depends(get_order_repo),
):
    """Customer rates a mechanic after service completion."""
    appointment = order_repo.get_appointment(rating_data.appointment_id)

    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    if appointment.customer_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only rate mechanics who served you")

    if appointment.status != AppointmentStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Can only rate completed appointments")

    rating = perf_service.add_customer_rating(
        mechanic_id=mechanic_id,
        customer_id=current_user.user_id,
        appointment_id=rating_data.appointment_id,
        rating=rating_data.rating,
        review=rating_data.review,
    )
    return {"message": "Rating submitted successfully", "rating_id": rating.id}


# ── Mechanic: my own performance ──────────────────────────────────────────────

@router.get("/my-performance")
def get_my_performance(
    shop_id: int,
    date_from: Optional[date] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    current_user: TokenData = Depends(get_current_user),
    shop_service: ShopService = Depends(get_shop_service),
    perf_service: MechanicPerformanceService = Depends(get_perf_service),
):
    """Mechanic views their own performance."""
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this shop")

    if not date_from:
        date_from = date.today() - timedelta(days=30)
    if not date_to:
        date_to = date.today()

    summary = perf_service.get_mechanic_performance_summary(current_user.user_id, shop_id, date_from, date_to)
    all_mechanics = perf_service.get_shop_mechanics_comparison(shop_id, date_from, date_to)

    my_rank = next(
        (i for i, m in enumerate(all_mechanics, 1) if m["mechanic_id"] == current_user.user_id),
        None,
    )

    return {
        "my_performance": summary,
        "my_rank": my_rank,
        "total_mechanics": len(all_mechanics),
    }
