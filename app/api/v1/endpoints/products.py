"""Product endpoints - Shop Owner only for write operations."""
from typing import List, Optional
import os
import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from sqlmodel import Session, select

from app.db import get_session
from app.models.product import Product, ProductCreate, ProductRead
from app.core.security import TokenData
from app.core.dependencies import require_shop_owner, require_shop_member
from app.services.image_storage_service import ImageStorageService

router = APIRouter(tags=["products"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB


# Helper function to get products query
def get_shop_products_query(session: Session, shop_id: int):
    """Get active products for a shop."""
    return select(Product).where(
        Product.shop_id == shop_id,
        Product.is_active
    )


@router.post("/shops/{shop_id}/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(
    shop_id: int,
    product_data: ProductCreate,
    current_user: TokenData = Depends(require_shop_owner),
    session: Session = Depends(get_session)
):
    """Create a new product in shop. Only shop owner can create."""
    product = Product(
        **product_data.model_dump(),
        shop_id=shop_id
    )
    session.add(product)
    session.commit()
    session.refresh(product)
    return product


@router.get("/shops/{shop_id}/products", response_model=List[ProductRead])
def list_products(
    shop_id: int,
    current_user: TokenData = Depends(require_shop_member),
    session: Session = Depends(get_session)
):
    """List all products in shop. Shop members (owner/mechanic) can view."""
    statement = get_shop_products_query(session, shop_id)
    products = session.exec(statement).all()
    return products


@router.get("/shops/{shop_id}/products/{product_id}", response_model=ProductRead)
def get_product(
    shop_id: int,
    product_id: int,
    current_user: TokenData = Depends(require_shop_member),
    session: Session = Depends(get_session)
):
    """Get product details. Shop members can view."""
    statement = select(Product).where(
        Product.id == product_id,
        Product.shop_id == shop_id,
        Product.is_active
    )
    product = session.exec(statement).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    return product


@router.put("/shops/{shop_id}/products/{product_id}", response_model=ProductRead)
def update_product(
    shop_id: int,
    product_id: int,
    product_data: ProductCreate,
    current_user: TokenData = Depends(require_shop_owner),
    session: Session = Depends(get_session)
):
    """Update product. Only shop owner can update."""
    statement = select(Product).where(
        Product.id == product_id,
        Product.shop_id == shop_id,
        Product.is_active
    )
    product = session.exec(statement).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Update fields
    for key, value in product_data.model_dump().items():
        setattr(product, key, value)
    
    session.commit()
    session.refresh(product)
    return product


@router.delete("/shops/{shop_id}/products/{product_id}")
def delete_product(
    shop_id: int,
    product_id: int,
    current_user: TokenData = Depends(require_shop_owner),
    session: Session = Depends(get_session)
):
    """Delete product (soft delete). Only shop owner can delete."""
    statement = select(Product).where(
        Product.id == product_id,
        Product.shop_id == shop_id,
        Product.is_active
    )
    product = session.exec(statement).first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    product.is_active = False
    session.commit()
    return {"message": "Product deleted successfully"}


@router.post("/shops/{shop_id}/products/{product_id}/image", response_model=ProductRead)
def upload_product_image(
    shop_id: int,
    product_id: int,
    image: UploadFile = File(...),
    current_user: TokenData = Depends(require_shop_owner),
    session: Session = Depends(get_session)
):
    """Upload or replace the image for a product.

    Send as **multipart/form-data** with an `image` field (JPEG / PNG / WebP, max 5 MB).
    The stored URL is returned in `image_url` and is ready to be forwarded to the
    image-search service for embedding generation.
    """
    statement = select(Product).where(
        Product.id == product_id,
        Product.shop_id == shop_id,
        Product.is_active
    )
    product = session.exec(statement).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image type '{image.content_type}'. Use JPEG, PNG or WebP.",
        )
    raw = image.file.read()
    if len(raw) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image must be smaller than 5 MB.",
        )

    result = ImageStorageService().upload(raw, folder="products")
    product.image_url = result["image_url"]
    product.thumbnail_url = result["thumbnail_url"]
    session.commit()
    session.refresh(product)

    # Automatically index the new image in the AI image search service
    IMAGE_SEARCH_API_URL = os.getenv("IMAGE_SEARCH_API_URL", "http://localhost:8001")
    try:
        with httpx.Client(timeout=15.0) as client:
            files = {"file": (image.filename, raw, image.content_type)}
            params = {
                "product_id": product.id,
                "category": product.category.name if product.category else "Uncategorized"
            }
            response = client.post(f"{IMAGE_SEARCH_API_URL}/update-index", files=files, params=params)
            response.raise_for_status()
    except Exception as exc:
        # Log the failure but don't fail the primary upload transaction
        print(f"Warning: Failed to update image search index for product {product.id}: {exc}")

    return product


# Product search and filter endpoints

@router.get("/shops/{shop_id}/products/search")
def search_products(
    shop_id: int,
    q: Optional[str] = Query(None, description="Search query"),
    category_id: Optional[int] = Query(None, description="Filter by category"),
    min_price: Optional[float] = Query(None, description="Minimum price"),
    max_price: Optional[float] = Query(None, description="Maximum price"),
    current_user: TokenData = Depends(require_shop_member),
    session: Session = Depends(get_session)
):
    """Search products with filters."""
    query = select(Product).where(
        Product.shop_id == shop_id,
        Product.is_active
    )
    
    if q:
        query = query.where(
            Product.name.ilike(f"%{q}%") | 
            Product.description.ilike(f"%{q}%")
        )
    
    if category_id:
        query = query.where(Product.category_id == category_id)
    
    if min_price is not None:
        query = query.where(Product.price >= min_price)
    
    if max_price is not None:
        query = query.where(Product.price <= max_price)
    
    products = session.exec(query).all()
    return products


@router.post("/shops/{shop_id}/products/search-by-image")
def search_products_by_image(
    shop_id: int,
    image: UploadFile = File(...),
    current_user: TokenData = Depends(require_shop_member),
    session: Session = Depends(get_session)
):
    """Search products by uploaded image (Visual Search) using CLIP + FAISS microservice."""
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
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
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


@router.get("/shops/{shop_id}/products/by-service/{service_id}")
def get_products_by_service(
    shop_id: int,
    service_id: int,
    current_user: TokenData = Depends(require_shop_member),
    session: Session = Depends(get_session)
):
    """Get product recommendations based on selected service."""
    from app.models.category import ServiceCategory, ProductCategory
    
    # Get categories linked to this service
    service_categories = session.exec(
        select(ProductCategory).join(
            ServiceCategory, ServiceCategory.category_id == ProductCategory.id
        ).where(
            ServiceCategory.service_id == service_id,
            ServiceCategory.is_active,
            ProductCategory.is_active
        ).order_by(ServiceCategory.priority.desc())
    ).all()
    
    if not service_categories:
        return {"message": "No product recommendations for this service", "products": []}
    
    # Get category IDs including children
    category_ids = []
    for cat in service_categories:
        category_ids.append(cat.id)
        # Add child categories
        children = session.exec(
            select(ProductCategory).where(
                ProductCategory.parent_id == cat.id,
                ProductCategory.is_active
            )
        ).all()
        category_ids.extend([c.id for c in children])
    
    # Get products in these categories
    products = session.exec(
        select(Product).where(
            Product.shop_id == shop_id,
            Product.category_id.in_(category_ids),
            Product.is_active
        )
    ).all()
    
    return {
        "service_id": service_id,
        "recommended_categories": [cat.name for cat in service_categories],
        "products": products
    }
