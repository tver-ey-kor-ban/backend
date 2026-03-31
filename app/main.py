import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.db import init_db, get_session
from app.api.v1.endpoints import auth, shops, products, services, vehicles, categories, customers, customer_vehicles, product_orders, mechanic_bookings, mechanic_performance, ratings, admin
from app.services.auth_service import AuthService
from app.core.vehicle_seeder import seed_vehicles
from app.core.test_data_seeder import seed_test_data
from app.models.user import UserCreate


def create_default_admin():
    """Create default admin account if it doesn't exist."""
    session = next(get_session())
    try:
        auth_service = AuthService(session)
        
        # Get admin credentials from environment or use defaults
        admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        
        # Check if admin already exists
        admin = auth_service.get_user_by_username(admin_username)
        if not admin:
            admin_data = UserCreate(
                email=admin_email,
                username=admin_username,
                password=admin_password,
                full_name="Administrator",
                roles="admin,user",
                is_active=True,
                is_superuser=True
            )
            auth_service.create_user(admin_data)
            print(f"Default admin account created: {admin_username}")
            if admin_password == "admin123":
                print("WARNING: Using default admin password. Please change it in production!")
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
    
    # Seed vehicle data
    session = next(get_session())
    try:
        seed_vehicles(session)
    finally:
        session.close()
    
    # Create default admin account
    create_default_admin()
    
    # Seed test data for team testing
    session = next(get_session())
    try:
        seed_test_data(session)
    finally:
        session.close()
    
    yield
    # Shutdown: cleanup if needed


app = FastAPI(title="Mobile App Backend", lifespan=lifespan)

# Configure CORS - use environment variable in production
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
if allowed_origins != "*":
    allowed_origins = [origin.strip() for origin in allowed_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include auth routes
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])

# Include shop routes
app.include_router(shops.router, prefix="/api/v1", tags=["shops"])

# Include product routes
app.include_router(products.router, prefix="/api/v1", tags=["products"])

# Include service routes
app.include_router(services.router, prefix="/api/v1", tags=["services"])

# Include vehicle routes
app.include_router(vehicles.router, prefix="/api/v1", tags=["vehicles"])

# Include category routes
app.include_router(categories.router, prefix="/api/v1", tags=["categories"])

# Include customer routes
app.include_router(customers.router, prefix="/api/v1", tags=["customers"])

# Include customer vehicle routes
app.include_router(customer_vehicles.router, prefix="/api/v1", tags=["customer-vehicles"])

# Include product order routes
app.include_router(product_orders.router, prefix="/api/v1", tags=["product-orders"])

# Include mechanic booking routes
app.include_router(mechanic_bookings.router, prefix="/api/v1", tags=["mechanic-bookings"])

# Include mechanic performance routes
app.include_router(mechanic_performance.router, prefix="/api/v1", tags=["mechanic-performance"])

# Include ratings routes
app.include_router(ratings.router, prefix="/api/v1", tags=["ratings"])

# Include admin routes
app.include_router(admin.router, prefix="/api/v1", tags=["admin"])


@app.get("/")
async def root():
    return {"message": "Backend is running"}