from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.db import init_db, get_session
from app.api.v1.endpoints import auth
from app.services.auth_service import AuthService
from app.models.user import UserCreate


def create_default_admin():
    """Create default admin account if it doesn't exist."""
    session = next(get_session())
    try:
        auth_service = AuthService(session)
        
        # Check if admin already exists
        admin = auth_service.get_user_by_username("admin")
        if not admin:
            admin_data = UserCreate(
                email="admin@example.com",
                username="admin",
                password="admin123",  # Change this in production!
                full_name="Administrator",
                roles="admin,user",
                is_active=True,
                is_superuser=True
            )
            auth_service.create_user(admin_data)
            print("Default admin account created: admin / admin123")
            print("WARNING: Please change the default admin password!")
    except Exception as e:
        print(f"Error creating default admin: {e}")
    finally:
        session.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup: Initialize database
    init_db()
    print("Database initialized successfully")
    
    # Create default admin account
    create_default_admin()
    
    yield
    # Shutdown: cleanup if needed


app = FastAPI(title="Mobile App Backend", lifespan=lifespan)

# Important for Flutter: Allow your app to communicate with the server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

<<<<<<< HEAD
# Include auth routes
=======
# Include Firebase auth routes only
>>>>>>> 02321203d4f15894a8f54db55c959a7cfc3436ae
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])


@app.get("/")
async def root():
    return {"message": "Backend is running"}