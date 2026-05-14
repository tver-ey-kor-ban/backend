from typing import Optional, List, Tuple
from sqlalchemy import func
from sqlmodel import Session, select

from app.models.shop import Shop, UserShop


class ShopRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, shop_id: int) -> Optional[Shop]:
        return self.session.get(Shop, shop_id)

    def get_all_active(self) -> List[Shop]:
        return self.session.exec(
            select(Shop).where(Shop.is_active)
        ).all()

    def get_all_active_paginated(self, page: int, limit: int) -> Tuple[List[Shop], int]:
        total = self.session.execute(
            select(func.count()).select_from(Shop).where(Shop.is_active)
        ).scalar() or 0
        offset = (page - 1) * limit
        shops = self.session.exec(
            select(Shop).where(Shop.is_active).offset(offset).limit(limit)
        ).all()
        return shops, total

    def save(self, shop: Shop) -> Shop:
        self.session.add(shop)
        self.session.commit()
        self.session.refresh(shop)
        return shop

    def update(self, shop: Shop) -> Shop:
        self.session.commit()
        self.session.refresh(shop)
        return shop

    def get_user_assignments(self, user_id: int) -> List[UserShop]:
        return self.session.exec(
            select(UserShop).where(
                UserShop.user_id == user_id,
                UserShop.is_active,
            )
        ).all()

    def get_user_shop(self, user_id: int, shop_id: int) -> Optional[UserShop]:
        return self.session.exec(
            select(UserShop).where(
                UserShop.user_id == user_id,
                UserShop.shop_id == shop_id,
            )
        ).first()

    def get_active_user_shop(self, user_id: int, shop_id: int) -> Optional[UserShop]:
        return self.session.exec(
            select(UserShop).where(
                UserShop.user_id == user_id,
                UserShop.shop_id == shop_id,
                UserShop.is_active,
            )
        ).first()

    def get_active_user_shop_by_role(
        self, user_id: int, shop_id: int, role: str
    ) -> Optional[UserShop]:
        return self.session.exec(
            select(UserShop).where(
                UserShop.user_id == user_id,
                UserShop.shop_id == shop_id,
                UserShop.role == role,
                UserShop.is_active,
            )
        ).first()

    def get_active_members(self, shop_id: int) -> List[UserShop]:
        return self.session.exec(
            select(UserShop).where(
                UserShop.shop_id == shop_id,
                UserShop.is_active,
            )
        ).all()

    def save_user_shop(self, user_shop: UserShop) -> UserShop:
        self.session.add(user_shop)
        self.session.commit()
        self.session.refresh(user_shop)
        return user_shop

    def update_user_shop(self, user_shop: UserShop) -> UserShop:
        self.session.commit()
        self.session.refresh(user_shop)
        return user_shop

    def stage_user_shop(self, user_shop: UserShop) -> None:
        """Stage a UserShop for insert as part of a larger transaction."""
        self.session.add(user_shop)
        self.session.flush()
