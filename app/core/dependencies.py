"""Common dependencies for role-based access control."""
from fastapi import Depends, HTTPException, status
from sqlmodel import Session

from app.db import get_session
from app.core.security import get_current_user, TokenData
from app.services.shop_service import ShopService


def require_shop_owner(
    shop_id: int,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Dependency to check if current user is shop owner.
    
    Usage:
        @router.post("/{shop_id}/products")
        def create_product(
            shop_id: int,
            current_user: TokenData = Depends(require_shop_owner)
        ):
            # User is confirmed as shop owner
            pass
    """
    shop_service = ShopService(session)
    
    if not shop_service.is_shop_owner(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop owner can perform this action"
        )
    
    return current_user


def require_shop_member(
    shop_id: int,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Dependency to check if current user is shop member (owner or mechanic).
    
    Usage:
        @router.get("/{shop_id}/products")
        def list_products(
            shop_id: int,
            current_user: TokenData = Depends(require_shop_member)
        ):
            # User is confirmed as shop member
            pass
    """
    shop_service = ShopService(session)
    
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this shop"
        )
    
    return current_user
