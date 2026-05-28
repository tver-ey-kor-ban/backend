"""Local Authentication endpoints (JWT with username/password)."""
import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.security import TokenData, get_current_user, require_admin
from app.db import get_session
from app.models.shop import UserShop
from app.models.user import UserCreate, UserRead, UserUpdate
from app.repositories.user_repository import UserRepository
from app.schemas.auth import Token, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(tags=["authentication"])

UPLOAD_DIR = "uploads/avatars"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB


class RefreshTokenRequest(BaseModel):
    """Refresh token request model."""

    refresh_token: str


def get_auth_service(session: Session = Depends(get_session)) -> AuthService:
    return AuthService(UserRepository(session))


@router.post("/register", response_model=UserRead)
def register(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Register a new user."""
    try:
        user = auth_service.create_user(user_data)
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Login with username and password."""
    result = auth_service.login(form_data.username, form_data.password)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return result


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: TokenData = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Get current authenticated user."""
    assert current_user.username is not None
    user = auth_service.get_user_by_username(current_user.username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put("/me", response_model=UserResponse)
def update_me(
    full_name: Optional[str] = Form(default=None),
    phone: Optional[str] = Form(default=None),
    email: Optional[str] = Form(default=None),
    image: Optional[UploadFile] = File(default=None),
    current_user: TokenData = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Update the current user's profile.

    Send as **multipart/form-data**. All fields are optional:
    - **full_name** – display name
    - **phone** – phone number
    - **email** – new email address (must be unique)
    - **image** – JPEG / PNG / WebP profile picture (max 5 MB)
    """
    assert current_user.username is not None
    user = auth_service.get_user_by_username(current_user.username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if email and email != user.email:
        if auth_service.get_user_by_email(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use.",
            )

    profile_image_url: Optional[str] = None
    if image is not None:
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
        ext = image.filename.rsplit(".", 1)[-1] if image.filename and "." in image.filename else "jpg"
        filename = f"{uuid.uuid4().hex}.{ext}"
        dest = os.path.join(UPLOAD_DIR, filename)
        with open(dest, "wb") as f:
            f.write(raw)
        profile_image_url = f"/uploads/avatars/{filename}"

    update_kwargs: dict = {}
    if full_name is not None:
        update_kwargs["full_name"] = full_name
    if phone is not None:
        update_kwargs["phone"] = phone
    if email is not None:
        update_kwargs["email"] = email
    if profile_image_url is not None:
        update_kwargs["profile_image_url"] = profile_image_url

    updated = auth_service.update_profile(user, UserUpdate(**update_kwargs))
    return updated


@router.get("/me/roles")
def get_my_roles(
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Get current user's roles including all shop memberships."""
    memberships = session.exec(
        select(UserShop).where(
            UserShop.user_id == current_user.user_id,
            UserShop.is_active,
        )
    ).all()

    shop_roles = [{"shop_id": m.shop_id, "role": m.role} for m in memberships]

    roles = list(current_user.roles)
    for m in memberships:
        if m.role not in roles:
            roles.append(m.role)

    return {
        "username": current_user.username,
        "roles": roles,
        "is_superuser": current_user.is_superuser,
        "shop_roles": shop_roles,
    }


@router.post("/refresh", response_model=Token)
def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Refresh access token using refresh token."""
    result = auth_service.refresh_access_token(request.refresh_token)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return result


@router.post("/logout")
def logout(
    request: RefreshTokenRequest,
    current_user: TokenData = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Logout user by revoking refresh token."""
    success = auth_service.revoke_refresh_token(request.refresh_token)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid refresh token",
        )
    return {"message": "Successfully logged out"}


@router.post("/logout-all")
def logout_all(
    current_user: TokenData = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Logout user from all devices by revoking all refresh tokens."""
    assert current_user.user_id is not None
    count = auth_service.revoke_all_user_refresh_tokens(current_user.user_id)
    return {
        "message": "Successfully logged out from all devices",
        "revoked_tokens": count,
    }


@router.get("/admin-only")
def admin_only(current_user: TokenData = Depends(require_admin)):
    """Admin only endpoint."""
    return {"message": "Hello Admin!", "user": current_user.username}
