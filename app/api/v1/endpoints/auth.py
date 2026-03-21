"""Local Authentication endpoints (JWT with username/password)."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session
from pydantic import BaseModel

from app.db import get_session
from app.schemas.auth import Token, UserResponse
from app.services.auth_service import AuthService
from app.models.user import UserCreate, UserRead
from app.core.security import get_current_user, require_admin, TokenData

router = APIRouter(tags=["authentication"])


class RefreshTokenRequest(BaseModel):
    """Refresh token request model."""
    refresh_token: str


def get_auth_service(session: Session = Depends(get_session)) -> AuthService:
    """Dependency to get auth service."""
    return AuthService(session)


@router.post("/register", response_model=UserRead)
def register(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Register a new user.
    
    Args:
        user_data: User registration data including password
        
    Returns:
        Created user (without password)
    """
    try:
        user = auth_service.create_user(user_data)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Login with username and password.
    
    Args:
        form_data: OAuth2 form with username and password
        
    Returns:
        JWT access token for backend API
    """
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
    auth_service: AuthService = Depends(get_auth_service)
):
    """Get current authenticated user."""
    from app.models.user import User
    from sqlmodel import select
    
    statement = select(User).where(User.username == current_user.username)
    user = auth_service.session.exec(statement).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.get("/me/roles")
def get_my_roles(current_user: TokenData = Depends(get_current_user)):
    """Get current user's roles from JWT token."""
    return {
        "username": current_user.username,
        "roles": current_user.roles,
        "is_superuser": current_user.is_superuser
    }


@router.post("/refresh", response_model=Token)
def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Refresh access token using refresh token.
    
    Args:
        request: Refresh token request containing the refresh token
        
    Returns:
        New access token
    """
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
    auth_service: AuthService = Depends(get_auth_service)
):
    """Logout user by revoking refresh token.
    
    Args:
        request: Refresh token request containing the refresh token to revoke
        
    Returns:
        Success message
    """
    success = auth_service.revoke_refresh_token(request.refresh_token)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid refresh token"
        )
    
    return {"message": "Successfully logged out"}


@router.post("/logout-all")
def logout_all(
    current_user: TokenData = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Logout user from all devices by revoking all refresh tokens.
    
    Returns:
        Success message with count of revoked tokens
    """
    count = auth_service.revoke_all_user_refresh_tokens(current_user.user_id)
    
    return {
        "message": "Successfully logged out from all devices",
        "revoked_tokens": count
    }


# Example protected routes with role-based access
@router.get("/admin-only")
def admin_only(current_user: TokenData = Depends(require_admin)):
    """Admin only endpoint."""
    return {"message": "Hello Admin!", "user": current_user.username}
