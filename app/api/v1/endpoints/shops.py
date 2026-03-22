"""Shop endpoints for Owner/Mechanic management."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.db import get_session
from app.models.shop import ShopCreate, ShopRead, UserShopCreate
from app.services.shop_service import ShopService
from app.core.security import get_current_user, TokenData

router = APIRouter(prefix="/shops", tags=["shops"])


def get_shop_service(session: Session = Depends(get_session)) -> ShopService:
    """Dependency to get shop service."""
    return ShopService(session)


@router.post("", response_model=ShopRead, status_code=status.HTTP_201_CREATED)
def create_shop(
    shop_data: ShopCreate,
    current_user: TokenData = Depends(get_current_user),
    shop_service: ShopService = Depends(get_shop_service)
):
    """Create a new shop. The current user becomes the owner."""
    shop = shop_service.create_shop(shop_data, current_user.user_id)
    return shop


@router.get("", response_model=List[ShopRead])
def list_shops(
    current_user: TokenData = Depends(get_current_user),
    shop_service: ShopService = Depends(get_shop_service)
):
    """List all active shops."""
    return shop_service.get_all_shops()


@router.get("/my-shops")
def list_my_shops(
    current_user: TokenData = Depends(get_current_user),
    shop_service: ShopService = Depends(get_shop_service)
):
    """List shops where current user is owner or mechanic."""
    user_shops = shop_service.get_user_shops(current_user.user_id)
    return [
        {
            "shop_id": us.shop_id,
            "shop_name": us.shop.name,
            "role": us.role,
            "is_active": us.is_active
        }
        for us in user_shops
    ]


@router.get("/{shop_id}", response_model=ShopRead)
def get_shop(
    shop_id: int,
    current_user: TokenData = Depends(get_current_user),
    shop_service: ShopService = Depends(get_shop_service)
):
    """Get shop details by ID."""
    shop = shop_service.get_shop_by_id(shop_id)
    if not shop or not shop.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found"
        )
    return shop


@router.put("/{shop_id}", response_model=ShopRead)
def update_shop(
    shop_id: int,
    shop_data: ShopCreate,
    current_user: TokenData = Depends(get_current_user),
    shop_service: ShopService = Depends(get_shop_service)
):
    """Update shop details. Only owner can update."""
    # Check if user is owner
    if not shop_service.is_shop_owner(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop owner can update shop details"
        )
    
    shop = shop_service.update_shop(shop_id, shop_data)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found"
        )
    return shop


@router.delete("/{shop_id}")
def delete_shop(
    shop_id: int,
    current_user: TokenData = Depends(get_current_user),
    shop_service: ShopService = Depends(get_shop_service)
):
    """Delete a shop (soft delete). Only owner can delete."""
    # Check if user is owner
    if not shop_service.is_shop_owner(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop owner can delete shop"
        )
    
    success = shop_service.delete_shop(shop_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found"
        )
    return {"message": "Shop deleted successfully"}


# Member management endpoints

@router.post("/{shop_id}/members")
def add_member(
    shop_id: int,
    assignment: UserShopCreate,
    current_user: TokenData = Depends(get_current_user),
    shop_service: ShopService = Depends(get_shop_service)
):
    """Add a member to shop. Only owner can add members."""
    # Check if user is owner
    if not shop_service.is_shop_owner(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop owner can add members"
        )
    
    # Ensure the assignment is for this shop
    if assignment.shop_id != shop_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shop ID mismatch"
        )
    
    # Validate role
    if assignment.role not in ["owner", "mechanic"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be 'owner' or 'mechanic'"
        )
    
    user_shop = shop_service.assign_user_to_shop(assignment)
    return {
        "message": f"User added as {assignment.role}",
        "user_shop": user_shop
    }


@router.get("/{shop_id}/members")
def list_members(
    shop_id: int,
    current_user: TokenData = Depends(get_current_user),
    shop_service: ShopService = Depends(get_shop_service)
):
    """List all members of a shop. Owner and mechanics can view."""
    # Check if user is member
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this shop"
        )
    
    members = shop_service.get_shop_users(shop_id)
    return [
        {
            "user_id": m.user_id,
            "username": m.user.username,
            "full_name": m.user.full_name,
            "role": m.role,
            "is_active": m.is_active
        }
        for m in members
    ]


@router.put("/{shop_id}/members/{user_id}/role")
def change_member_role(
    shop_id: int,
    user_id: int,
    new_role: str,
    current_user: TokenData = Depends(get_current_user),
    shop_service: ShopService = Depends(get_shop_service)
):
    """Change a member's role. Only owner can change roles."""
    # Check if user is owner
    if not shop_service.is_shop_owner(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop owner can change member roles"
        )
    
    # Validate role
    if new_role not in ["owner", "mechanic"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be 'owner' or 'mechanic'"
        )
    
    user_shop = shop_service.change_user_role(user_id, shop_id, new_role)
    if not user_shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    return {"message": f"Role updated to {new_role}"}


@router.delete("/{shop_id}/members/{user_id}")
def remove_member(
    shop_id: int,
    user_id: int,
    current_user: TokenData = Depends(get_current_user),
    shop_service: ShopService = Depends(get_shop_service)
):
    """Remove a member from shop. Only owner can remove members."""
    # Check if user is owner
    if not shop_service.is_shop_owner(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop owner can remove members"
        )
    
    success = shop_service.remove_user_from_shop(user_id, shop_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    return {"message": "Member removed successfully"}
