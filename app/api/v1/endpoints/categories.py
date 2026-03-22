"""Product Category endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.db import get_session
from app.models.category import (
    ProductCategory, ProductCategoryCreate, ProductCategoryRead,
    ProductCategoryWithChildren, ServiceCategory, ServiceCategoryCreate
)
from app.core.dependencies import require_shop_owner

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("", response_model=ProductCategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    category_data: ProductCategoryCreate,
    current_user = Depends(require_shop_owner),
    session: Session = Depends(get_session)
):
    """Create a new product category."""
    category = ProductCategory(**category_data.model_dump())
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


@router.get("", response_model=List[ProductCategoryRead])
def list_categories(
    parent_id: Optional[int] = None,
    session: Session = Depends(get_session)
):
    """List all categories, optionally filtered by parent."""
    query = select(ProductCategory).where(ProductCategory.is_active)
    
    if parent_id is not None:
        query = query.where(ProductCategory.parent_id == parent_id)
    else:
        # Get only root categories (no parent)
        query = query.where(ProductCategory.parent_id.is_(None))
    
    return session.exec(query).all()


@router.get("/tree", response_model=List[ProductCategoryWithChildren])
def get_category_tree(
    session: Session = Depends(get_session)
):
    """Get full category tree with nested children."""
    def build_tree(parent_id: Optional[int] = None) -> List[ProductCategoryWithChildren]:
        query = select(ProductCategory).where(
            ProductCategory.parent_id == parent_id,
            ProductCategory.is_active
        )
        categories = session.exec(query).all()
        
        result = []
        for cat in categories:
            cat_dict = {
                "id": cat.id,
                "name": cat.name,
                "description": cat.description,
                "icon": cat.icon,
                "is_active": cat.is_active,
                "parent_id": cat.parent_id,
                "created_at": cat.created_at,
                "full_path": cat.full_path,
                "children": build_tree(cat.id)
            }
            result.append(cat_dict)
        return result
    
    return build_tree()


@router.get("/{category_id}", response_model=ProductCategoryRead)
def get_category(
    category_id: int,
    session: Session = Depends(get_session)
):
    """Get category by ID."""
    category = session.get(ProductCategory, category_id)
    if not category or not category.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    return category


@router.put("/{category_id}", response_model=ProductCategoryRead)
def update_category(
    category_id: int,
    category_data: ProductCategoryCreate,
    current_user = Depends(require_shop_owner),
    session: Session = Depends(get_session)
):
    """Update category."""
    category = session.get(ProductCategory, category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    for key, value in category_data.model_dump().items():
        setattr(category, key, value)
    
    session.commit()
    session.refresh(category)
    return category


@router.delete("/{category_id}")
def delete_category(
    category_id: int,
    current_user = Depends(require_shop_owner),
    session: Session = Depends(get_session)
):
    """Soft delete category."""
    category = session.get(ProductCategory, category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    category.is_active = False
    session.commit()
    return {"message": "Category deleted successfully"}


# Service-Category recommendation links

@router.post("/service-links", status_code=status.HTTP_201_CREATED)
def link_service_to_category(
    link_data: ServiceCategoryCreate,
    current_user = Depends(require_shop_owner),
    session: Session = Depends(get_session)
):
    """Link a service to a product category for recommendations."""
    link = ServiceCategory(**link_data.model_dump())
    session.add(link)
    session.commit()
    session.refresh(link)
    return {"message": "Service linked to category", "link": link}


@router.get("/by-service/{service_id}")
def get_categories_by_service(
    service_id: int,
    session: Session = Depends(get_session)
):
    """Get product categories linked to a service (for recommendations)."""
    query = select(ProductCategory, ServiceCategory).join(
        ServiceCategory, ServiceCategory.category_id == ProductCategory.id
    ).where(
        ServiceCategory.service_id == service_id,
        ServiceCategory.is_active,
        ProductCategory.is_active
    ).order_by(ServiceCategory.priority.desc())
    
    results = session.exec(query).all()
    
    return [
        {
            "category_id": cat.id,
            "category_name": cat.name,
            "priority": link.priority,
            "full_path": cat.full_path
        }
        for cat, link in results
    ]


@router.get("/{category_id}/products")
def get_products_by_category(
    category_id: int,
    include_subcategories: bool = True,
    session: Session = Depends(get_session)
):
    """Get all products in a category."""
    from app.models.product import Product
    
    category_ids = [category_id]
    
    if include_subcategories:
        # Get all child category IDs
        def get_children(parent_id: int):
            children = session.exec(
                select(ProductCategory).where(
                    ProductCategory.parent_id == parent_id,
                    ProductCategory.is_active
                )
            ).all()
            for child in children:
                category_ids.append(child.id)
                get_children(child.id)
        
        get_children(category_id)
    
    products = session.exec(
        select(Product).where(
            Product.category_id.in_(category_ids),
            Product.is_active
        )
    ).all()
    
    return products
