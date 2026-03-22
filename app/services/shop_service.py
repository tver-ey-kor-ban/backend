"""Shop service for managing workshops and user roles."""
from typing import Optional, List
from sqlmodel import Session, select

from app.models.shop import Shop, ShopCreate, UserShop, UserShopCreate


class ShopService:
    """Service for shop and user-shop relationship operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    # Shop operations
    def create_shop(self, shop_data: ShopCreate, owner_id: int) -> Shop:
        """Create a new shop with an owner."""
        # Create shop
        shop = Shop(**shop_data.model_dump())
        self.session.add(shop)
        self.session.commit()
        self.session.refresh(shop)
        
        # Assign owner
        user_shop = UserShop(
            user_id=owner_id,
            shop_id=shop.id,
            role="owner",
            is_active=True
        )
        self.session.add(user_shop)
        self.session.commit()
        
        return shop
    
    def get_shop_by_id(self, shop_id: int) -> Optional[Shop]:
        """Get shop by ID."""
        return self.session.get(Shop, shop_id)
    
    def get_all_shops(self) -> List[Shop]:
        """Get all shops."""
        statement = select(Shop).where(Shop.is_active)
        return self.session.exec(statement).all()
    
    def get_user_shops(self, user_id: int) -> List[UserShop]:
        """Get all shop relationships for a user."""
        statement = select(UserShop).where(
            UserShop.user_id == user_id,
            UserShop.is_active
        )
        return self.session.exec(statement).all()
    
    def update_shop(self, shop_id: int, shop_data: ShopCreate) -> Optional[Shop]:
        """Update shop details."""
        shop = self.get_shop_by_id(shop_id)
        if not shop:
            return None
        
        for key, value in shop_data.model_dump().items():
            setattr(shop, key, value)
        
        self.session.commit()
        self.session.refresh(shop)
        return shop
    
    def delete_shop(self, shop_id: int) -> bool:
        """Soft delete a shop."""
        shop = self.get_shop_by_id(shop_id)
        if not shop:
            return False
        
        shop.is_active = False
        self.session.commit()
        return True
    
    # User-Shop role operations
    def assign_user_to_shop(self, assignment: UserShopCreate) -> UserShop:
        """Assign a user to a shop with a role."""
        # Check if assignment already exists
        statement = select(UserShop).where(
            UserShop.user_id == assignment.user_id,
            UserShop.shop_id == assignment.shop_id
        )
        existing = self.session.exec(statement).first()
        
        if existing:
            # Update existing assignment
            existing.role = assignment.role
            existing.is_active
            self.session.commit()
            self.session.refresh(existing)
            return existing
        
        # Create new assignment
        user_shop = UserShop(**assignment.model_dump())
        self.session.add(user_shop)
        self.session.commit()
        self.session.refresh(user_shop)
        return user_shop
    
    def remove_user_from_shop(self, user_id: int, shop_id: int) -> bool:
        """Remove a user from a shop (soft delete)."""
        statement = select(UserShop).where(
            UserShop.user_id == user_id,
            UserShop.shop_id == shop_id,
            UserShop.is_active
        )
        user_shop = self.session.exec(statement).first()
        
        if not user_shop:
            return False
        
        user_shop.is_active = False
        self.session.commit()
        return True
    
    def get_shop_users(self, shop_id: int) -> List[UserShop]:
        """Get all users assigned to a shop."""
        statement = select(UserShop).where(
            UserShop.shop_id == shop_id,
            UserShop.is_active
        )
        return self.session.exec(statement).all()
    
    def change_user_role(self, user_id: int, shop_id: int, new_role: str) -> Optional[UserShop]:
        """Change a user's role in a shop."""
        statement = select(UserShop).where(
            UserShop.user_id == user_id,
            UserShop.shop_id == shop_id,
            UserShop.is_active
        )
        user_shop = self.session.exec(statement).first()
        
        if not user_shop:
            return None
        
        user_shop.role = new_role
        self.session.commit()
        self.session.refresh(user_shop)
        return user_shop
    
    # Permission checks
    def is_shop_owner(self, user_id: int, shop_id: int) -> bool:
        """Check if user is owner of a shop."""
        statement = select(UserShop).where(
            UserShop.user_id == user_id,
            UserShop.shop_id == shop_id,
            UserShop.role == "owner",
            UserShop.is_active
        )
        return self.session.exec(statement).first() is not None
    
    def is_shop_mechanic(self, user_id: int, shop_id: int) -> bool:
        """Check if user is mechanic in a shop."""
        statement = select(UserShop).where(
            UserShop.user_id == user_id,
            UserShop.shop_id == shop_id,
            UserShop.role == "mechanic",
            UserShop.is_active
        )
        return self.session.exec(statement).first() is not None
    
    def is_shop_member(self, user_id: int, shop_id: int) -> bool:
        """Check if user is a member (owner or mechanic) of a shop."""
        statement = select(UserShop).where(
            UserShop.user_id == user_id,
            UserShop.shop_id == shop_id,
            UserShop.is_active
        )
        return self.session.exec(statement).first() is not None
    
    def is_shop_customer(self, user_id: int, shop_id: int) -> bool:
        """Check if user is a customer of a shop."""
        statement = select(UserShop).where(
            UserShop.user_id == user_id,
            UserShop.shop_id == shop_id,
            UserShop.role == "customer",
            UserShop.is_active
        )
        return self.session.exec(statement).first() is not None
