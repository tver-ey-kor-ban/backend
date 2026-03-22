"""Product Category models for organizing garage products."""
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from app.models.product import Product


class ProductCategoryBase(SQLModel):
    """Base product category model."""
    name: str = Field(index=True)
    description: Optional[str] = None
    icon: Optional[str] = None  # Icon URL or class
    is_active: bool = True
    parent_id: Optional[int] = Field(default=None, foreign_key="product_categories.id")


class ProductCategory(ProductCategoryBase, table=True):
    """Product category database model."""
    __tablename__ = "product_categories"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    # Relationships
    products: List["Product"] = Relationship(back_populates="category")
    parent: Optional["ProductCategory"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "ProductCategory.id"}
    )
    children: List["ProductCategory"] = Relationship(back_populates="parent")
    
    @property
    def full_path(self) -> str:
        """Get full category path (e.g., 'Engine > Oil > Synthetic')."""
        if self.parent:
            return f"{self.parent.full_path} > {self.name}"
        return self.name


class ProductCategoryCreate(ProductCategoryBase):
    """Product category creation model."""
    pass


class ProductCategoryRead(ProductCategoryBase):
    """Product category read model."""
    id: int
    created_at: datetime
    full_path: Optional[str] = None


class ProductCategoryWithChildren(ProductCategoryRead):
    """Category with nested children."""
    children: List["ProductCategoryWithChildren"] = []


# Service-Category relationship for recommendations
class ServiceCategory(SQLModel, table=True):
    """Link services to product categories for recommendations."""
    __tablename__ = "service_categories"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    service_id: int = Field(foreign_key="services.id")
    category_id: int = Field(foreign_key="product_categories.id")
    priority: int = Field(default=1)  # Higher = more relevant
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ServiceCategoryCreate(SQLModel):
    """Service-category link creation."""
    service_id: int
    category_id: int
    priority: int = 1


class ServiceCategoryRead(SQLModel):
    """Service-category link read."""
    id: int
    service_id: int
    category_id: int
    priority: int
    category_name: str
