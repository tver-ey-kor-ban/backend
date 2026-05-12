"""Rating endpoints for products and services."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session

from app.db import get_session
from app.core.security import get_current_user, TokenData
from app.repositories.rating_repository import RatingRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.shop_repository import ShopRepository
from app.repositories.user_repository import UserRepository
from app.services.rating_service import RatingService
from app.services.shop_service import ShopService
from app.models.ratings import ProductRatingCreate, ServiceRatingCreate

router = APIRouter(prefix="/ratings", tags=["ratings"])


def get_rating_service(session: Session = Depends(get_session)) -> RatingService:
    return RatingService(
        RatingRepository(session),
        OrderRepository(session),
        ProductRepository(session),
    )


def get_shop_service(session: Session = Depends(get_session)) -> ShopService:
    return ShopService(ShopRepository(session))


def get_user_repo(session: Session = Depends(get_session)) -> UserRepository:
    return UserRepository(session)


def get_rating_repo(session: Session = Depends(get_session)) -> RatingRepository:
    return RatingRepository(session)


def get_product_repo(session: Session = Depends(get_session)) -> ProductRepository:
    return ProductRepository(session)


# ── Product ratings ───────────────────────────────────────────────────────────

@router.post("/products")
def rate_product(
    rating_data: ProductRatingCreate,
    current_user: TokenData = Depends(get_current_user),
    rating_service: RatingService = Depends(get_rating_service),
):
    """Rate a product (customer only, after purchase)."""
    try:
        rating = rating_service.rate_product(
            customer_id=current_user.user_id,
            product_id=rating_data.product_id,
            rating=rating_data.rating,
            review=rating_data.review,
            order_id=rating_data.order_id,
        )
        return {"message": "Product rated successfully", "rating_id": rating.id}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/products/{product_id}/summary")
def get_product_rating_summary(
    product_id: int,
    rating_service: RatingService = Depends(get_rating_service),
):
    """Get rating summary for a product (public)."""
    return rating_service.get_product_rating_summary(product_id)


@router.get("/products/{product_id}/reviews")
def get_product_reviews(
    product_id: int,
    limit: int = Query(20, ge=1, le=100),
    rating_service: RatingService = Depends(get_rating_service),
    user_repo: UserRepository = Depends(get_user_repo),
):
    """Get reviews for a product (public)."""
    reviews = rating_service.get_product_reviews(product_id, limit)
    result = []
    for review in reviews:
        customer = user_repo.get_by_id(review.customer_id)
        result.append({
            "id": review.id,
            "customer_name": customer.full_name if customer else "Anonymous",
            "rating": review.rating,
            "review": review.review,
            "created_at": review.created_at,
        })
    return {"product_id": product_id, "reviews": result}


# ── Service ratings ───────────────────────────────────────────────────────────

@router.post("/services")
def rate_service(
    rating_data: ServiceRatingCreate,
    current_user: TokenData = Depends(get_current_user),
    rating_service: RatingService = Depends(get_rating_service),
):
    """Rate a service (customer only, after appointment completed)."""
    try:
        rating = rating_service.rate_service(
            customer_id=current_user.user_id,
            service_id=rating_data.service_id,
            rating=rating_data.rating,
            review=rating_data.review,
            appointment_id=rating_data.appointment_id,
        )
        return {"message": "Service rated successfully", "rating_id": rating.id}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/services/{service_id}/summary")
def get_service_rating_summary(
    service_id: int,
    rating_service: RatingService = Depends(get_rating_service),
):
    """Get rating summary for a service (public)."""
    return rating_service.get_service_rating_summary(service_id)


@router.get("/services/{service_id}/reviews")
def get_service_reviews(
    service_id: int,
    limit: int = Query(20, ge=1, le=100),
    rating_service: RatingService = Depends(get_rating_service),
    user_repo: UserRepository = Depends(get_user_repo),
):
    """Get reviews for a service (public)."""
    reviews = rating_service.get_service_reviews(service_id, limit)
    result = []
    for review in reviews:
        customer = user_repo.get_by_id(review.customer_id)
        result.append({
            "id": review.id,
            "customer_name": customer.full_name if customer else "Anonymous",
            "rating": review.rating,
            "review": review.review,
            "created_at": review.created_at,
        })
    return {"service_id": service_id, "reviews": result}


# ── Shop owner: top rated ─────────────────────────────────────────────────────

@router.get("/shops/{shop_id}/top-products")
def get_shop_top_rated_products(
    shop_id: int,
    limit: int = Query(10, ge=1, le=50),
    current_user: TokenData = Depends(get_current_user),
    shop_service: ShopService = Depends(get_shop_service),
    rating_service: RatingService = Depends(get_rating_service),
):
    """Get top rated products in a shop (Owner only)."""
    if not shop_service.is_shop_owner(current_user.user_id, shop_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only shop owner can view ratings")

    return {"shop_id": shop_id, "top_products": rating_service.get_shop_top_rated_products(shop_id, limit)}


@router.get("/shops/{shop_id}/top-services")
def get_shop_top_rated_services(
    shop_id: int,
    limit: int = Query(10, ge=1, le=50),
    current_user: TokenData = Depends(get_current_user),
    shop_service: ShopService = Depends(get_shop_service),
    rating_service: RatingService = Depends(get_rating_service),
):
    """Get top rated services in a shop (Owner only)."""
    if not shop_service.is_shop_owner(current_user.user_id, shop_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only shop owner can view ratings")

    return {"shop_id": shop_id, "top_services": rating_service.get_shop_top_rated_services(shop_id, limit)}


# ── Customer: my ratings ──────────────────────────────────────────────────────

@router.get("/my-ratings")
def get_my_ratings(
    current_user: TokenData = Depends(get_current_user),
    rating_repo: RatingRepository = Depends(get_rating_repo),
    product_repo: ProductRepository = Depends(get_product_repo),
):
    """Get all ratings submitted by current customer."""
    product_ratings = rating_repo.get_product_ratings_by_customer(current_user.user_id)
    service_ratings = rating_repo.get_service_ratings_by_customer(current_user.user_id)

    product_results = []
    for r in product_ratings:
        product = product_repo.get_product(r.product_id)
        product_results.append({
            "id": r.id,
            "type": "product",
            "item_id": r.product_id,
            "item_name": product.name if product else "Unknown",
            "rating": r.rating,
            "review": r.review,
            "created_at": r.created_at,
        })

    service_results = []
    for r in service_ratings:
        service = product_repo.get_service(r.service_id)
        service_results.append({
            "id": r.id,
            "type": "service",
            "item_id": r.service_id,
            "item_name": service.name if service else "Unknown",
            "rating": r.rating,
            "review": r.review,
            "created_at": r.created_at,
        })

    return {
        "product_ratings": product_results,
        "service_ratings": service_results,
        "total": len(product_results) + len(service_results),
    }
