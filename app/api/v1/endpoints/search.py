"""Global search endpoint — searches products and services across all active shops."""
from fastapi import APIRouter, Depends, Query, File, UploadFile, HTTPException
from sqlalchemy import func
import os
import httpx
from sqlmodel import Session, select

from app.db import get_session

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
def global_search(
    q: str = Query(..., min_length=1, description="Search term"),
    type: str = Query("all", regex="^(products|services|all)$", description="Filter by type"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    """Search products and/or services across all active shops (PUBLIC).

    - `type=products` — products only
    - `type=services` — services only
    - `type=all`      — both, interleaved up to `limit` items
    """
    from app.models.product import Product, Service
    from app.models.shop import Shop
    from app.models.ratings import ProductRating, ServiceRating

    items = []
    total = 0

    if type in ("products", "all"):
        prod_limit = limit if type == "products" else limit // 2
        prod_offset = (page - 1) * prod_limit if type == "products" else 0

        prod_conditions = [
            Product.is_active,
            Shop.is_active,
            Product.name.ilike(f"%{q}%") | Product.description.ilike(f"%{q}%"),
        ]

        prod_total = session.execute(
            select(func.count())
            .select_from(Product)
            .join(Shop, Shop.id == Product.shop_id)
            .where(*prod_conditions)
        ).scalar() or 0
        total += prod_total

        prod_rows = session.execute(
            select(
                Product,
                Shop,
                func.coalesce(func.avg(ProductRating.rating), 0.0).label("avg_rating"),
                func.count(ProductRating.id).label("rating_count"),
            )
            .join(Shop, Shop.id == Product.shop_id)
            .outerjoin(ProductRating, ProductRating.product_id == Product.id)
            .where(*prod_conditions)
            .group_by(Product.id, Shop.id)
            .offset(prod_offset)
            .limit(prod_limit)
        ).all()

        for row in prod_rows:
            items.append(
                {
                    "type": "product",
                    "id": row.Product.id,
                    "name": row.Product.name,
                    "description": row.Product.description,
                    "price": row.Product.price,
                    "image_url": row.Product.image_url,
                    "is_available": row.Product.is_active and row.Product.stock_quantity > 0,
                    "stock_quantity": row.Product.stock_quantity,
                    "rating": round(float(row.avg_rating), 1),
                    "rating_count": row.rating_count,
                    "shop": {
                        "id": row.Shop.id,
                        "name": row.Shop.name,
                        "address": row.Shop.address,
                    },
                }
            )

    if type in ("services", "all"):
        svc_limit = limit if type == "services" else limit - len(items)
        svc_offset = (page - 1) * svc_limit if type == "services" else 0

        svc_conditions = [
            Service.is_active,
            Shop.is_active,
            Service.name.ilike(f"%{q}%") | Service.description.ilike(f"%{q}%"),
        ]

        svc_total = session.execute(
            select(func.count())
            .select_from(Service)
            .join(Shop, Shop.id == Service.shop_id)
            .where(*svc_conditions)
        ).scalar() or 0
        total += svc_total

        svc_rows = session.execute(
            select(
                Service,
                Shop,
                func.coalesce(func.avg(ServiceRating.rating), 0.0).label("avg_rating"),
                func.count(ServiceRating.id).label("rating_count"),
            )
            .join(Shop, Shop.id == Service.shop_id)
            .outerjoin(ServiceRating, ServiceRating.service_id == Service.id)
            .where(*svc_conditions)
            .group_by(Service.id, Shop.id)
            .offset(svc_offset)
            .limit(max(svc_limit, 0))
        ).all()

        for row in svc_rows:
            items.append(
                {
                    "type": "service",
                    "id": row.Service.id,
                    "name": row.Service.name,
                    "description": row.Service.description,
                    "price": row.Service.price,
                    "estimated_duration_minutes": row.Service.duration_minutes,
                    "service_type": row.Service.service_type,
                    "image_url": row.Service.image_url,
                    "is_available": row.Service.is_active,
                    "rating": round(float(row.avg_rating), 1),
                    "rating_count": row.rating_count,
                    "shop": {
                        "id": row.Shop.id,
                        "name": row.Shop.name,
                        "address": row.Shop.address,
                    },
                }
            )

    return {"items": items, "total": total, "page": page, "limit": limit}


@router.post("/image")
def search_products_by_image(
    shop_id: int = Query(..., description="The shop ID to search products from"),
    image: UploadFile = File(...),
    session: Session = Depends(get_session)
):
    """Search products by uploaded image (Visual Search) using CLIP + FAISS microservice (PUBLIC)."""
    from app.models.product import Product

    image_contents = image.file.read()
    image.file.seek(0)

    IMAGE_SEARCH_API_URL = os.getenv("IMAGE_SEARCH_API_URL", "http://localhost:8001")

    try:
        with httpx.Client(timeout=15.0) as client:
            files = {"file": (image.filename, image_contents, image.content_type)}
            response = client.post(f"{IMAGE_SEARCH_API_URL}/image-search", files=files)
            response.raise_for_status()
            search_data = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Image search service is currently unavailable: {exc}"
        )

    results = search_data.get("results", [])
    if not results:
        return {
            "message": "No matching products found",
            "uploaded_filename": image.filename,
            "results": [],
            "total": 0
        }

    similarity_map = {res["product_id"]: res["similarity"] for res in results}
    product_ids = list(similarity_map.keys())

    db_products = session.exec(
        select(Product).where(
            Product.id.in_(product_ids),
            Product.shop_id == shop_id,
            Product.is_active == True
        )
    ).all()

    search_results = []
    for product in db_products:
        prod_dict = {
            "id": product.id,
            "shop_id": product.shop_id,
            "name": product.name,
            "description": product.description,
            "price": product.price,
            "cost": product.cost,
            "stock_quantity": product.stock_quantity,
            "sku": product.sku,
            "is_active": product.is_active,
            "category_id": product.category_id,
            "image_url": product.image_url,
            "thumbnail_url": product.thumbnail_url,
            "created_at": product.created_at.isoformat() if product.created_at else None,
            "similarity": similarity_map.get(product.id, 0.0),
            "category": product.category.name if product.category else None
        }
        search_results.append(prod_dict)

    # Sort results by similarity descending
    search_results.sort(key=lambda x: x["similarity"], reverse=True)

    return {
        "message": "Image search completed successfully",
        "uploaded_filename": image.filename,
        "results": search_results,
        "total": len(search_results)
    }
