from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.db import init_db, get_session
from app.api.v1.endpoints import auth, shops, products, services, vehicles, categories, customers, customer_vehicles, product_orders, mechanic_bookings, mechanic_performance, ratings, admin
from app.services.auth_service import AuthService
from app.core.vehicle_seeder import seed_vehicles
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
    
    # Seed vehicle data
    session = next(get_session())
    try:
        seed_vehicles(session)
    finally:
        session.close()
    
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