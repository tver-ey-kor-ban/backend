from datetime import datetime, timedelta
from typing import Optional, List
from jose import JWTError, jwt
import bcrypt
import secrets
from pydantic import BaseModel
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# Configuration
SECRET_KEY = "your_super_secret_jwt_key_here"  # Move to env in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class TokenData(BaseModel):
    """Token data extracted from JWT."""
    user_id: Optional[int] = None
    username: Optional[str] = None
    email: Optional[str] = None
    roles: List[str] = []
    is_superuser: bool = False


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    # bcrypt has a 72 byte limit, truncate if necessary
    password_bytes = plain_password.encode('utf-8')[:72]
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    # bcrypt has a 72 byte limit, truncate if necessary
    password_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def create_access_token(
    user_id: int,
    username: str,
    email: str,
    roles: List[str] = None,
    is_superuser: bool = False,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token with user roles."""
    if roles is None:
        roles = ["user"]  # Default role
    
    to_encode = {
        "sub": username,
        "user_id": user_id,
        "email": email,
        "roles": roles,
        "is_superuser": is_superuser,
        "type": "access"
    }
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(user_id: int) -> str:
    """Create a JWT refresh token with unique jti."""
    to_encode = {
        "user_id": user_id,
        "type": "refresh",
        "jti": secrets.token_urlsafe(16)  # Unique identifier for each token
    }
    
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_refresh_token(token: str) -> Optional[int]:
    """Decode and verify a refresh token. Returns user_id if valid."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_type: str = payload.get("type")
        if token_type != "refresh":
            return None
        return payload.get("user_id")
    except JWTError:
        return None


def decode_access_token(token: str) -> Optional[TokenData]:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return TokenData(
            user_id=payload.get("user_id"),
            username=username,
            email=payload.get("email"),
            roles=payload.get("roles", []),
            is_superuser=payload.get("is_superuser", False)
        )
    except JWTError:
        return None


async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    """Get current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data = decode_access_token(token)
    if token_data is None:
        raise credentials_exception
    
    return token_data


def require_roles(required_roles: List[str]):
    """Dependency factory to check if user has required roles."""
    async def role_checker(current_user: TokenData = Depends(get_current_user)):
        # Superusers bypass role checks
        if current_user.is_superuser:
            return current_user
        
        # Check if user has any of the required roles
        user_roles = set(current_user.roles)
        required = set(required_roles)
        
        if not user_roles.intersection(required):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {required_roles}"
            )
        return current_user
    return role_checker


# Common role requirements
require_admin = require_roles(["admin"])
require_moderator = require_roles(["admin", "moderator"])
require_premium = require_roles(["admin", "premium", "moderator"])
