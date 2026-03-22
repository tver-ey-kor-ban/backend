"""Product endpoints - Shop Owner only for write operations."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from sqlmodel import Session, select

from app.db import get_session
from app.models.product import Product, ProductCreate, ProductRead
from app.core.security import TokenData
from app.core.dependencies import require_shop_owner, require_shop_member

router = APIRouter(tags=["products"])


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
    """Search products by uploaded image (Visual Search).
    
    This is a placeholder for image-based search.
    In production, you would:
    1. Upload image to cloud storage
    2. Generate image embedding using ML model (CLIP, etc.)
    3. Compare embedding with product image embeddings
    4. Return most similar products
    """
    # TODO: Implement actual image search with ML
    # For now, return products with images as placeholder
    
    products = session.exec(
        select(Product).where(
            Product.shop_id == shop_id,
            Product.is_active,
            Product.image_url.isnot(None)
        )
    ).all()
    
    return {
        "message": "Image search placeholder - returning products with images",
        "uploaded_filename": image.filename,
        "results": products[:10]  # Limit results
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
