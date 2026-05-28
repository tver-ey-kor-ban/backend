from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str = "bearer"
    refresh_token: str | None = None


class UserLogin(BaseModel):
    """User login request model."""
    username: str
    password: str


class UserRegister(BaseModel):
    """User registration request model."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    full_name: str | None = None


class UserResponse(BaseModel):
    """User response model."""
    id: int
    email: str
    username: str
    full_name: str | None
    phone: str | None = None
    profile_image_url: str | None = None
    is_active: bool

    class Config:
        from_attributes = True
