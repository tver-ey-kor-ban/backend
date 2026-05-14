"""Shop service for managing workshops and user roles."""
from typing import Optional, List

from app.models.shop import Shop, ShopCreate, UserShop, UserShopCreate
from app.repositories.shop_repository import ShopRepository


class ShopService:
    def __init__(self, shop_repo: ShopRepository):
        self.shop_repo = shop_repo

    # ── Shop operations ──────────────────────────────────────────────────────

    def create_shop(self, shop_data: ShopCreate, owner_id: int) -> Shop:
        shop = self.shop_repo.save(Shop(**shop_data.model_dump()))
        self.shop_repo.save_user_shop(
            UserShop(user_id=owner_id, shop_id=shop.id, role="owner", is_active=True)
        )
        return shop

    def get_shop_by_id(self, shop_id: int) -> Optional[Shop]:
        return self.shop_repo.get_by_id(shop_id)

    def get_all_shops(self) -> List[Shop]:
        return self.shop_repo.get_all_active()

    def get_all_shops_paginated(self, page: int, limit: int):
        return self.shop_repo.get_all_active_paginated(page, limit)

    def get_user_shops(self, user_id: int) -> List[UserShop]:
        return self.shop_repo.get_user_assignments(user_id)

    def update_shop(self, shop_id: int, shop_data: ShopCreate) -> Optional[Shop]:
        shop = self.shop_repo.get_by_id(shop_id)
        if not shop:
            return None
        for key, value in shop_data.model_dump().items():
            setattr(shop, key, value)
        return self.shop_repo.update(shop)

    def delete_shop(self, shop_id: int) -> bool:
        shop = self.shop_repo.get_by_id(shop_id)
        if not shop:
            return False
        shop.is_active = False
        self.shop_repo.update(shop)
        return True

    # ── User-Shop role operations ─────────────────────────────────────────────

    def assign_user_to_shop(self, assignment: UserShopCreate) -> UserShop:
        existing = self.shop_repo.get_user_shop(assignment.user_id, assignment.shop_id)
        if existing:
            existing.role = assignment.role
            existing.is_active = True
            return self.shop_repo.update_user_shop(existing)
        return self.shop_repo.save_user_shop(UserShop(**assignment.model_dump()))

    def remove_user_from_shop(self, user_id: int, shop_id: int) -> bool:
        user_shop = self.shop_repo.get_active_user_shop(user_id, shop_id)
        if not user_shop:
            return False
        user_shop.is_active = False
        self.shop_repo.update_user_shop(user_shop)
        return True

    def get_shop_users(self, shop_id: int) -> List[UserShop]:
        return self.shop_repo.get_active_members(shop_id)

    def change_user_role(self, user_id: int, shop_id: int, new_role: str) -> Optional[UserShop]:
        user_shop = self.shop_repo.get_active_user_shop(user_id, shop_id)
        if not user_shop:
            return None
        user_shop.role = new_role
        return self.shop_repo.update_user_shop(user_shop)

    # ── Permission checks ─────────────────────────────────────────────────────

    def is_shop_owner(self, user_id: int, shop_id: int) -> bool:
        return self.shop_repo.get_active_user_shop_by_role(user_id, shop_id, "owner") is not None

    def is_shop_mechanic(self, user_id: int, shop_id: int) -> bool:
        return self.shop_repo.get_active_user_shop_by_role(user_id, shop_id, "mechanic") is not None

    def is_shop_member(self, user_id: int, shop_id: int) -> bool:
        return self.shop_repo.get_active_user_shop(user_id, shop_id) is not None

    def is_shop_customer(self, user_id: int, shop_id: int) -> bool:
        return self.shop_repo.get_active_user_shop_by_role(user_id, shop_id, "customer") is not None
