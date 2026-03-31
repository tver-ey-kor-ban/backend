"""Seed test data for team testing."""
from sqlmodel import Session, select
from datetime import datetime, timedelta

from app.models.user import User
from app.models.shop import Shop, UserShop, ShopRole
from app.models.product import Product, Service
from app.models.category import ProductCategory
from app.models.appointment import Appointment
from app.models.product_order import ProductOrder, ProductOrderItem
from app.core.security import get_password_hash


def seed_test_data(session: Session):
    """Seed database with test accounts and sample data."""
    
    # Check if test data already exists
    existing_owner = session.exec(select(User).where(User.username == "owner1")).first()
    if existing_owner:
        print("Test data already seeded")
        return
    
    print("Creating test accounts and data...")
    
    # ========== TEST USERS ==========
    
    # Owner user
    owner_password = get_password_hash("owner123")
    print(f"DEBUG: owner1 password hash: {owner_password}")
    owner = User(
        email="owner@test.com",
        username="owner1",
        hashed_password=owner_password,
        full_name="Test Shop Owner",
        roles="user",
        is_active=True,
        is_superuser=False
    )
    session.add(owner)
    session.flush()
    
    # Mechanic user
    mechanic = User(
        email="mechanic@test.com",
        username="mechanic1",
        hashed_password=get_password_hash("mechanic123"),
        full_name="Test Mechanic",
        roles="user",
        is_active=True,
        is_superuser=False
    )
    session.add(mechanic)
    session.flush()
    
    # Customer user
    customer = User(
        email="customer@test.com",
        username="customer1",
        hashed_password=get_password_hash("customer123"),
        full_name="Test Customer",
        roles="user",
        is_active=True,
        is_superuser=False
    )
    session.add(customer)
    session.flush()
    
    print("✓ Created test users: owner1, mechanic1, customer1")
    
    # ========== SHOP ==========
    
    shop = Shop(
        name="Test Garage",
        address="123 Test Street, Test City",
        phone="+1234567890",
        email="garage@test.com",
        description="A test garage for team testing",
        is_active=True
    )
    session.add(shop)
    session.flush()
    
    # Assign owner to shop
    owner_shop = UserShop(
        user_id=owner.id,
        shop_id=shop.id,
        role=ShopRole.OWNER
    )
    session.add(owner_shop)
    
    # Assign mechanic to shop
    mechanic_shop = UserShop(
        user_id=mechanic.id,
        shop_id=shop.id,
        role=ShopRole.MECHANIC
    )
    session.add(mechanic_shop)
    session.flush()
    
    print(f"✓ Created shop: {shop.name} (ID: {shop.id})")
    
    # ========== PRODUCT CATEGORIES ==========
    
    categories = [
        ProductCategory(name="Engine Oil", description="Motor oils and lubricants"),
        ProductCategory(name="Brake Parts", description="Brake pads, rotors, and fluids"),
        ProductCategory(name="Filters", description="Air, oil, and fuel filters"),
        ProductCategory(name="Tires", description="Car tires and wheels"),
    ]
    
    for cat in categories:
        session.add(cat)
    session.flush()
    
    print(f"✓ Created {len(categories)} product categories")
    
    # ========== PRODUCTS ==========
    
    products = [
        Product(
            shop_id=shop.id,
            category_id=categories[0].id,
            name="Synthetic Oil 5W-30",
            description="Full synthetic motor oil",
            price=29.99,
            stock_quantity=50,
            sku="OIL-5W30-001",
            is_active=True
        ),
        Product(
            shop_id=shop.id,
            category_id=categories[1].id,
            name="Brake Pads - Front",
            description="Ceramic brake pads for front wheels",
            price=49.99,
            stock_quantity=20,
            sku="BRAKE-FRONT-001",
            is_active=True
        ),
        Product(
            shop_id=shop.id,
            category_id=categories[2].id,
            name="Air Filter",
            description="Engine air filter",
            price=15.99,
            stock_quantity=30,
            sku="FILTER-AIR-001",
            is_active=True
        ),
    ]
    
    for prod in products:
        session.add(prod)
    session.flush()
    
    print(f"✓ Created {len(products)} products")
    
    # ========== SERVICES ==========
    
    services = [
        Service(
            shop_id=shop.id,
            name="Oil Change",
            description="Full oil change with filter replacement",
            price=39.99,
            duration_minutes=30,
            service_type="shop_based",
            is_active=True
        ),
        Service(
            shop_id=shop.id,
            name="Brake Replacement",
            description="Replace brake pads and inspect rotors",
            price=89.99,
            duration_minutes=60,
            service_type="shop_based",
            is_active=True
        ),
        Service(
            shop_id=shop.id,
            name="Mobile Oil Change",
            description="We come to you! Oil change at your location",
            price=59.99,
            duration_minutes=45,
            service_type="mobile",
            mobile_service_fee=20.00,
            is_active=True
        ),
    ]
    
    for svc in services:
        session.add(svc)
    session.flush()
    
    print(f"✓ Created {len(services)} services")
    
    # ========== SAMPLE APPOINTMENT ==========
    
    appointment = Appointment(
        shop_id=shop.id,
        customer_id=customer.id,
        appointment_date=datetime.utcnow() + timedelta(days=1),
        status="pending",
        vehicle_make="Toyota",
        vehicle_model="Camry",
        vehicle_year=2020,
        total_price=39.99,
        notes="Please check the brakes as well"
    )
    session.add(appointment)
    session.flush()
    
    print("✓ Created sample appointment")
    
    # ========== SAMPLE PRODUCT ORDER ==========
    
    order = ProductOrder(
        shop_id=shop.id,
        customer_id=customer.id,
        status="pending",
        total_amount=29.99,
        pickup_date=datetime.utcnow() + timedelta(days=2),
        notes="Call me when ready"
    )
    session.add(order)
    session.flush()
    
    # Add order item
    order_item = ProductOrderItem(
        order_id=order.id,
        product_id=products[0].id,
        quantity=1,
        unit_price=29.99,
        total_price=29.99,
        product_name=products[0].name,
        product_sku=products[0].sku
    )
    session.add(order_item)
    session.flush()
    
    print("✓ Created sample product order")
    
    session.commit()
    
    print("\n" + "="*50)
    print("TEST ACCOUNTS READY!")
    print("="*50)
    print("Admin:    admin / admin123")
    print("Owner:    owner1 / owner123")
    print("Mechanic: mechanic1 / mechanic123")
    print("Customer: customer1 / customer123")
    print("="*50)
    print(f"Shop ID: {shop.id}")
    print("API Base: http://localhost:8000")
    print("API Docs: http://localhost:8000/docs")
    print("="*50)
