"""Rating endpoints for products and services."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select

from app.db import get_session
from app.core.security import get_current_user, TokenData
from app.services.rating_service import RatingService
from app.models.ratings import (
    ProductRatingCreate, ServiceRatingCreate
)

router = APIRouter(prefix="/ratings", tags=["ratings"])


# ==================== PRODUCT RATINGS ====================

@router.post("/products")
def rate_product(
    rating_data: ProductRatingCreate,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Rate a product (customer only, after purchase)."""
    rating_service = RatingService(session)
    
    try:
        rating = rating_service.rate_product(
            customer_id=current_user.user_id,
            product_id=rating_data.product_id,
            rating=rating_data.rating,
            review=rating_data.review,
            order_id=rating_data.order_id
        )
        
        return {
            "message": "Product rated successfully",
            "rating_id": rating.id
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/products/{product_id}/summary")
def get_product_rating_summary(
    product_id: int,
    session: Session = Depends(get_session)
):
    """Get rating summary for a product (public)."""
    rating_service = RatingService(session)
    summary = rating_service.get_product_rating_summary(product_id)
    return summary


@router.get("/products/{product_id}/reviews")
def get_product_reviews(
    product_id: int,
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session)
):
    """Get reviews for a product (public)."""
    from app.models.user import User
    
    rating_service = RatingService(session)
    reviews = rating_service.get_product_reviews(product_id, limit)
    
    # Enrich with customer names
    result = []
    for review in reviews:
        customer = session.get(User, review.customer_id)
        result.append({
            "id": review.id,
            "customer_name": customer.full_name if customer else "Anonymous",
            "rating": review.rating,
            "review": review.review,
            "created_at": review.created_at
        })
    
    return {
        "product_id": product_id,
        "reviews": result
    }


# ==================== SERVICE RATINGS ====================

@router.post("/services")
def rate_service(
    rating_data: ServiceRatingCreate,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Rate a service (customer only, after appointment completed)."""
    rating_service = RatingService(session)
    
    try:
        rating = rating_service.rate_service(
            customer_id=current_user.user_id,
            service_id=rating_data.service_id,
            rating=rating_data.rating,
            review=rating_data.review,
            appointment_id=rating_data.appointment_id
        )
        
        return {
            "message": "Service rated successfully",
            "rating_id": rating.id
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/services/{service_id}/summary")
def get_service_rating_summary(
    service_id: int,
    session: Session = Depends(get_session)
):
    """Get rating summary for a service (public)."""
    rating_service = RatingService(session)
    summary = rating_service.get_service_rating_summary(service_id)
    return summary


@router.get("/services/{service_id}/reviews")
def get_service_reviews(
    service_id: int,
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session)
):
    """Get reviews for a service (public)."""
    from app.models.user import User
    
    rating_service = RatingService(session)
    reviews = rating_service.get_service_reviews(service_id, limit)
    
    # Enrich with customer names
    result = []
    for review in reviews:
        customer = session.get(User, review.customer_id)
        result.append({
            "id": review.id,
            "customer_name": customer.full_name if customer else "Anonymous",
            "rating": review.rating,
            "review": review.review,
            "created_at": review.created_at
        })
    
    return {
        "service_id": service_id,
        "reviews": result
    }


# ==================== SHOP OWNER: TOP RATED ====================

@router.get("/shops/{shop_id}/top-products")
def get_shop_top_rated_products(
    shop_id: int,
    limit: int = Query(10, ge=1, le=50),
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get top rated products in a shop (Owner only)."""
    from app.services.shop_service import ShopService
    
    shop_service = ShopService(session)
    
    if not shop_service.is_shop_owner(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop owner can view ratings"
        )
    
    rating_service = RatingService(session)
    top_products = rating_service.get_shop_top_rated_products(shop_id, limit)
    
    return {
        "shop_id": shop_id,
        "top_products": top_products
    }


@router.get("/shops/{shop_id}/top-services")
def get_shop_top_rated_services(
    shop_id: int,
    limit: int = Query(10, ge=1, le=50),
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get top rated services in a shop (Owner only)."""
    from app.services.shop_service import ShopService
    
    shop_service = ShopService(session)
    
    if not shop_service.is_shop_owner(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop owner can view ratings"
        )
    
    rating_service = RatingService(session)
    top_services = rating_service.get_shop_top_rated_services(shop_id, limit)
    
    return {
        "shop_id": shop_id,
        "top_services": top_services
    }


# ==================== CUSTOMER: MY RATINGS ====================

@router.get("/my-ratings")
def get_my_ratings(
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get all ratings submitted by current customer."""
    from app.models.ratings import ProductRating, ServiceRating
    from app.models.product import Product, Service as ServiceModel
    
    # Get product ratings
    product_ratings = session.exec(
        select(ProductRating).where(
            ProductRating.customer_id == current_user.user_id
        ).order_by(ProductRating.created_at.desc())
    ).all()
    
    # Get service ratings
    service_ratings = session.exec(
        select(ServiceRating).where(
            ServiceRating.customer_id == current_user.user_id
        ).order_by(ServiceRating.created_at.desc())
    ).all()
    
    # Enrich with names
    product_results = []
    for r in product_ratings:
        product = session.get(Product, r.product_id)
        product_results.append({
            "id": r.id,
            "type": "product",
            "item_id": r.product_id,
            "item_name": product.name if product else "Unknown",
            "rating": r.rating,
            "review": r.review,
            "created_at": r.created_at
        })
    
    service_results = []
    for r in service_ratings:
        service = session.get(ServiceModel, r.service_id)
        service_results.append({
            "id": r.id,
            "type": "service",
            "item_id": r.service_id,
            "item_name": service.name if service else "Unknown",
            "rating": r.rating,
            "review": r.review,
            "created_at": r.created_at
        })
    
    return {
        "product_ratings": product_results,
        "service_ratings": service_results,
        "total": len(product_results) + len(service_results)
    }
