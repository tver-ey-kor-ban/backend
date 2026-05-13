"""Seed demo data for professor presentation."""
from sqlmodel import Session, select
from datetime import datetime, timedelta

from app.models.user import User
from app.models.shop import Shop, UserShop, ShopRole
from app.models.product import Product, Service
from app.models.category import ProductCategory
from app.models.appointment import Appointment, AppointmentStatus, ServiceHistory
from app.models.product_order import ProductOrder, ProductOrderItem
from app.models.invoice import Invoice, InvoiceItem, Payment, InvoiceStatus, PaymentMethod
from app.models.ratings import ProductRating, ServiceRating
from app.core.security import get_password_hash


def seed_test_data(session: Session):
    """Seed database with realistic demo data."""

    existing = session.exec(select(User).where(User.username == "owner1")).first()
    if existing:
        print("Test data already seeded")
        return

    print("Creating demo data...")
    now = datetime.utcnow()

    # ========== USERS ==========

    owner = User(email="james@autocare.com", username="owner1",
                 hashed_password=get_password_hash("owner123"),
                 full_name="James Wilson", roles="user", is_active=True)
    owner2 = User(email="sarah@speedfix.com", username="owner2",
                  hashed_password=get_password_hash("owner123"),
                  full_name="Sarah Chen", roles="user", is_active=True)
    mechanic1 = User(email="mike@autocare.com", username="mechanic1",
                     hashed_password=get_password_hash("mechanic123"),
                     full_name="Mike Johnson", roles="user", is_active=True)
    mechanic2 = User(email="dave@autocare.com", username="mechanic2",
                     hashed_password=get_password_hash("mechanic123"),
                     full_name="Dave Martinez", roles="user", is_active=True)
    mechanic3 = User(email="lisa@speedfix.com", username="mechanic3",
                     hashed_password=get_password_hash("mechanic123"),
                     full_name="Lisa Park", roles="user", is_active=True)
    customer1 = User(email="alex@gmail.com", username="customer1",
                     hashed_password=get_password_hash("customer123"),
                     full_name="Alex Thompson", roles="user", is_active=True)
    customer2 = User(email="maria@gmail.com", username="customer2",
                     hashed_password=get_password_hash("customer123"),
                     full_name="Maria Garcia", roles="user", is_active=True)
    customer3 = User(email="john@gmail.com", username="customer3",
                     hashed_password=get_password_hash("customer123"),
                     full_name="John Smith", roles="user", is_active=True)

    for u in [owner, owner2, mechanic1, mechanic2, mechanic3, customer1, customer2, customer3]:
        session.add(u)
    session.flush()
    print("✓ Created 8 users (2 owners, 3 mechanics, 3 customers)")

    # ========== SHOPS ==========

    shop1 = Shop(name="AutoCare Pro",
                 address="456 Main Street, Downtown",
                 phone="+1-555-0101", email="info@autocare.com",
                 description="Certified mechanics, all makes and models. Trusted since 2010.",
                 is_active=True)
    shop2 = Shop(name="SpeedFix Garage",
                 address="789 Oak Avenue, Westside",
                 phone="+1-555-0202", email="info@speedfix.com",
                 description="Fast, reliable repairs. Same-day service available.",
                 is_active=True)

    session.add(shop1)
    session.add(shop2)
    session.flush()

    for user_id, shop_id, role in [
        (owner.id,    shop1.id, ShopRole.OWNER),
        (mechanic1.id, shop1.id, ShopRole.MECHANIC),
        (mechanic2.id, shop1.id, ShopRole.MECHANIC),
        (owner2.id,   shop2.id, ShopRole.OWNER),
        (mechanic3.id, shop2.id, ShopRole.MECHANIC),
    ]:
        session.add(UserShop(user_id=user_id, shop_id=shop_id, role=role))
    session.flush()
    print("✓ Created 2 shops (AutoCare Pro, SpeedFix Garage)")

    # ========== CATEGORIES ==========

    cats = [
        ProductCategory(name="Engine Oil",  description="Motor oils and lubricants"),
        ProductCategory(name="Brake Parts", description="Brake pads, rotors, and fluids"),
        ProductCategory(name="Filters",     description="Air, oil, fuel, and cabin filters"),
        ProductCategory(name="Tires",       description="Car tires and wheels"),
        ProductCategory(name="Batteries",   description="Car batteries and accessories"),
    ]
    for c in cats:
        session.add(c)
    session.flush()
    oil_cat, brake_cat, filter_cat, tire_cat, battery_cat = cats
    print(f"✓ Created {len(cats)} categories")

    # ========== PRODUCTS ==========

    products = [
        Product(shop_id=shop1.id, category_id=oil_cat.id,
                name="Mobil 1 Synthetic 5W-30 (5qt)",
                description="Full synthetic motor oil for high-performance engines",
                price=34.99, cost=22.00, stock_quantity=80, sku="OIL-M1-5W30", is_active=True),
        Product(shop_id=shop1.id, category_id=oil_cat.id,
                name="Castrol GTX 10W-40 (5qt)",
                description="Conventional oil, ideal for older vehicles",
                price=24.99, cost=14.00, stock_quantity=60, sku="OIL-GTX-10W40", is_active=True),
        Product(shop_id=shop1.id, category_id=brake_cat.id,
                name="Bosch QuietCast Brake Pads (Front)",
                description="Ceramic pads with anti-squeal shims",
                price=54.99, cost=32.00, stock_quantity=25, sku="BRAKE-BQ-FRONT", is_active=True),
        Product(shop_id=shop1.id, category_id=brake_cat.id,
                name="Bosch QuietCast Brake Pads (Rear)",
                description="Ceramic rear brake pads",
                price=44.99, cost=26.00, stock_quantity=20, sku="BRAKE-BQ-REAR", is_active=True),
        Product(shop_id=shop1.id, category_id=filter_cat.id,
                name="K&N High-Performance Air Filter",
                description="Washable, reusable performance air filter",
                price=49.99, cost=28.00, stock_quantity=15, sku="FILTER-KN-AIR", is_active=True),
        Product(shop_id=shop1.id, category_id=filter_cat.id,
                name="OEM Oil Filter",
                description="Standard replacement oil filter, universal fit",
                price=8.99, cost=3.50, stock_quantity=100, sku="FILTER-OIL-OEM", is_active=True),
        Product(shop_id=shop1.id, category_id=battery_cat.id,
                name="DieHard Platinum Battery (Group 35)",
                description="AGM battery, 3-year free replacement warranty",
                price=189.99, cost=110.00, stock_quantity=10, sku="BATT-DH-GRP35", is_active=True),
        Product(shop_id=shop1.id, category_id=tire_cat.id,
                name="Michelin Pilot Sport 4 (225/45R17)",
                description="Ultra-high performance summer tire",
                price=179.99, cost=115.00, stock_quantity=12, sku="TIRE-MPS4-225", is_active=True),
    ]
    for p in products:
        session.add(p)
    session.flush()
    p_oil, p_oil2, p_brake_f, p_brake_r, p_air, p_oilfilter, p_battery, p_tire = products
    print(f"✓ Created {len(products)} products")

    # ========== SERVICES ==========

    services = [
        Service(shop_id=shop1.id, name="Full Oil Change",
                description="Drain & replace oil + filter, top up fluids, 21-point inspection",
                price=49.99, duration_minutes=30, service_type="shop_based", is_active=True),
        Service(shop_id=shop1.id, name="Brake Pad Replacement",
                description="Replace front or rear brake pads, inspect rotors and callipers",
                price=149.99, duration_minutes=90, service_type="shop_based", is_active=True),
        Service(shop_id=shop1.id, name="Full Brake Service",
                description="All 4 brake pads replaced, rotors machined/replaced, fluid bled",
                price=349.99, duration_minutes=180, service_type="shop_based", is_active=True),
        Service(shop_id=shop1.id, name="Battery Replacement",
                description="Battery load test + install new battery, reset electronics",
                price=39.99, duration_minutes=30, service_type="shop_based", is_active=True),
        Service(shop_id=shop1.id, name="Tire Rotation & Balance",
                description="Rotate all 4 tires and dynamically balance each wheel",
                price=59.99, duration_minutes=60, service_type="shop_based", is_active=True),
        Service(shop_id=shop1.id, name="Mobile Oil Change",
                description="We come to your home or office — full oil change on-site",
                price=69.99, duration_minutes=45, service_type="mobile",
                mobile_service_fee=20.00, is_active=True),
        Service(shop_id=shop1.id, name="Full Vehicle Inspection",
                description="50-point inspection with written report and photo evidence",
                price=89.99, duration_minutes=90, service_type="shop_based", is_active=True),
    ]
    for s in services:
        session.add(s)
    session.flush()
    svc_oil, svc_brake, svc_full_brake, svc_battery, svc_tire, svc_mobile, svc_inspect = services
    print(f"✓ Created {len(services)} services")

    # ========== APPOINTMENTS ==========
    # Variety of statuses: completed (past), in_progress (today), confirmed + pending (future)

    appt_rows = [
        # --- COMPLETED (past) ---
        Appointment(shop_id=shop1.id, customer_id=customer1.id, service_id=svc_oil.id,
                    vehicle_info="Toyota Camry 2021",
                    appointment_date=now - timedelta(days=45),
                    status=AppointmentStatus.COMPLETED,
                    service_price=49.99, tax_amount=5.00, total_amount=54.99,
                    notes="Regular maintenance visit"),
        Appointment(shop_id=shop1.id, customer_id=customer2.id, service_id=svc_brake.id,
                    vehicle_info="Honda Civic 2019",
                    appointment_date=now - timedelta(days=30),
                    status=AppointmentStatus.COMPLETED,
                    service_price=149.99, tax_amount=15.00, total_amount=164.99,
                    notes="Front brakes worn to 10%, urgent replacement"),
        Appointment(shop_id=shop1.id, customer_id=customer3.id, service_id=svc_inspect.id,
                    vehicle_info="Ford F-150 2022",
                    appointment_date=now - timedelta(days=14),
                    status=AppointmentStatus.COMPLETED,
                    service_price=89.99, tax_amount=9.00, total_amount=98.99,
                    notes="Pre-purchase inspection for used vehicle"),
        Appointment(shop_id=shop1.id, customer_id=customer1.id, service_id=svc_tire.id,
                    vehicle_info="Toyota Camry 2021",
                    appointment_date=now - timedelta(days=7),
                    status=AppointmentStatus.COMPLETED,
                    service_price=59.99, tax_amount=6.00, total_amount=65.99,
                    notes="Seasonal rotation"),
        # --- IN PROGRESS (today) ---
        Appointment(shop_id=shop1.id, customer_id=customer2.id, service_id=svc_full_brake.id,
                    vehicle_info="Honda Civic 2019",
                    appointment_date=now - timedelta(hours=1),
                    status=AppointmentStatus.IN_PROGRESS,
                    service_price=349.99, tax_amount=35.00, total_amount=384.99,
                    notes="Full brake overhaul, customer waiting"),
        # --- CONFIRMED (upcoming) ---
        Appointment(shop_id=shop1.id, customer_id=customer3.id, service_id=svc_oil.id,
                    vehicle_info="Ford F-150 2022",
                    appointment_date=now + timedelta(days=2),
                    status=AppointmentStatus.CONFIRMED,
                    service_price=49.99, tax_amount=5.00, total_amount=54.99,
                    notes=""),
        Appointment(shop_id=shop1.id, customer_id=customer1.id, service_id=svc_battery.id,
                    vehicle_info="Toyota Camry 2021",
                    appointment_date=now + timedelta(days=3),
                    status=AppointmentStatus.CONFIRMED,
                    service_price=39.99, tax_amount=4.00, total_amount=43.99,
                    notes="Battery showing low voltage on cold mornings"),
        # --- PENDING (awaiting confirmation) ---
        Appointment(shop_id=shop1.id, customer_id=customer2.id, service_id=svc_mobile.id,
                    vehicle_info="Honda Civic 2019",
                    appointment_date=now + timedelta(days=5),
                    status=AppointmentStatus.PENDING,
                    service_price=69.99, mobile_service_fee=20.00,
                    tax_amount=9.00, total_amount=98.99,
                    notes="Home address: 42 Oak Street, please call before arriving"),
        Appointment(shop_id=shop1.id, customer_id=customer3.id, service_id=svc_inspect.id,
                    vehicle_info="Toyota RAV4 2020",
                    appointment_date=now + timedelta(days=6),
                    status=AppointmentStatus.PENDING,
                    service_price=89.99, tax_amount=9.00, total_amount=98.99,
                    notes="Buying this car — need full inspection"),
    ]

    for a in appt_rows:
        session.add(a)
    session.flush()
    completed = [a for a in appt_rows if a.status == AppointmentStatus.COMPLETED]
    print(f"✓ Created {len(appt_rows)} appointments "
          f"({len(completed)} completed, 1 in-progress, rest upcoming)")

    # ========== SERVICE HISTORY for completed appointments ==========

    for appt in completed:
        svc = session.get(Service, appt.service_id)
        session.add(ServiceHistory(
            shop_id=appt.shop_id,
            customer_id=appt.customer_id,
            appointment_id=appt.id,
            service_name=svc.name if svc else "Service",
            service_description=svc.description if svc else None,
            price=appt.total_amount or 0,
            completed_date=appt.appointment_date,
            notes=appt.notes,
        ))
    session.flush()

    # ========== INVOICES for completed appointments ==========

    for i, appt in enumerate(completed, start=1):
        inv = Invoice(
            shop_id=shop1.id,
            customer_id=appt.customer_id,
            appointment_id=appt.id,
            invoice_number=f"INV-2025-{i:04d}",
            status=InvoiceStatus.PAID,
            service_cost=appt.service_price or 0,
            tax_amount=appt.tax_amount or 0,
            total_amount=appt.total_amount or 0,
            amount_paid=appt.total_amount or 0,
            paid_at=appt.appointment_date + timedelta(hours=1),
            due_date=appt.appointment_date + timedelta(days=7),
        )
        session.add(inv)
        session.flush()

        session.add(InvoiceItem(
            invoice_id=inv.id, item_type="service", name="Service",
            quantity=1.0, unit_price=appt.service_price or 0,
            total_price=appt.service_price or 0,
        ))
        if appt.tax_amount:
            session.add(InvoiceItem(
                invoice_id=inv.id, item_type="tax", name="Tax (10%)",
                quantity=1.0, unit_price=appt.tax_amount,
                total_price=appt.tax_amount,
            ))
        session.add(Payment(
            invoice_id=inv.id,
            amount=appt.total_amount or 0,
            method=PaymentMethod.CARD,
            reference=f"TXN-{10000 + i}",
        ))
    session.flush()
    print(f"✓ Created {len(completed)} invoices (all paid)")

    # ========== PRODUCT ORDERS ==========

    orders_spec = [
        dict(customer_id=customer1.id, status="completed",
             total_amount=p_oil.price + p_oilfilter.price,
             pickup_date=now - timedelta(days=20), notes="",
             items=[(p_oil, 1), (p_oilfilter, 1)]),
        dict(customer_id=customer2.id, status="ready",
             total_amount=p_brake_f.price,
             pickup_date=now + timedelta(days=1), notes="Call when ready for pickup",
             items=[(p_brake_f, 1)]),
        dict(customer_id=customer3.id, status="pending",
             total_amount=p_oil.price * 2,
             pickup_date=now + timedelta(days=4), notes="",
             items=[(p_oil, 2)]),
    ]

    orders = []
    for spec in orders_spec:
        order = ProductOrder(
            shop_id=shop1.id,
            customer_id=spec["customer_id"],
            status=spec["status"],
            total_amount=spec["total_amount"],
            pickup_date=spec["pickup_date"],
            notes=spec["notes"],
        )
        session.add(order)
        session.flush()
        orders.append(order)
        for product, qty in spec["items"]:
            session.add(ProductOrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=qty,
                unit_price=product.price,
                total_price=product.price * qty,
                product_name=product.name,
                product_sku=product.sku,
            ))
    session.flush()
    print(f"✓ Created {len(orders)} product orders")

    # ========== RATINGS ==========

    service_ratings = [
        (svc_oil.id,   customer1.id, appt_rows[0].id, 5,
         "Quick and professional — oil change done in under 30 minutes. Will come back!"),
        (svc_brake.id, customer2.id, appt_rows[1].id, 5,
         "Excellent work. Brakes feel brand new. Highly recommend AutoCare Pro!"),
        (svc_inspect.id, customer3.id, appt_rows[2].id, 4,
         "Very thorough inspection with a clear written report. Great value for money."),
        (svc_tire.id, customer1.id, appt_rows[3].id, 5,
         "They noticed my front tires were wearing unevenly and rotated accordingly. Saved me money!"),
    ]
    for svc_id, cust_id, appt_id, rating, review in service_ratings:
        session.add(ServiceRating(service_id=svc_id, customer_id=cust_id,
                                  appointment_id=appt_id, rating=rating, review=review))

    product_ratings = [
        (p_oil.id,       customer1.id, orders[0].id, 5,
         "Great quality oil — engine runs noticeably smoother."),
        (p_oilfilter.id, customer1.id, orders[0].id, 4,
         "OEM quality as expected, fits perfectly."),
    ]
    for prod_id, cust_id, order_id, rating, review in product_ratings:
        session.add(ProductRating(product_id=prod_id, customer_id=cust_id,
                                  order_id=order_id, rating=rating, review=review))

    session.flush()
    print("✓ Created ratings and reviews")

    session.commit()

    print("\n" + "=" * 58)
    print("  DEMO DATA READY FOR PRESENTATION")
    print("=" * 58)
    print("  Admin:     admin      / admin123")
    print("  Owner:     owner1     / owner123")
    print("  Mechanic:  mechanic1  / mechanic123")
    print("  Mechanic:  mechanic2  / mechanic123")
    print("  Customer:  customer1  / customer123  (Alex Thompson)")
    print("  Customer:  customer2  / customer123  (Maria Garcia)")
    print("  Customer:  customer3  / customer123  (John Smith)")
    print("=" * 58)
    print(f"  Shops:        AutoCare Pro (ID {shop1.id}), SpeedFix (ID {shop2.id})")
    print(f"  Products:     {len(products)} items across 5 categories")
    print(f"  Services:     {len(services)} (shop-based + mobile)")
    print(f"  Appointments: {len(appt_rows)} total — {len(completed)} completed, 1 in-progress, rest upcoming")
    print(f"  Invoices:     {len(completed)} (all paid)")
    print(f"  Orders:       {len(orders)} (completed / ready / pending)")
    print(f"  Ratings:      {len(service_ratings)} service + {len(product_ratings)} product")
    print("=" * 58)
