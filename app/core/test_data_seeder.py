"""Seed demo data — makes the app feel like real users are actively using it."""
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
from app.models.customer_vehicle import CustomerVehicle
from app.models.chat import ChatRoom, ChatMessage, ChatRoomType
from app.models.notification import Notification, NotificationType, NotificationStatus
from app.models.quotation import Quotation, QuotationItem, QuotationStatus
from app.models.repair_progress import RepairProgress, RepairProgressUpdate, RepairStage
from app.models.mechanic_performance import MechanicPerformance, MechanicRating
from app.core.security import get_password_hash

# ---------------------------------------------------------------------------
# Placeholder image URLs
# ---------------------------------------------------------------------------
_AVA = "https://api.dicebear.com/7.x/initials/svg?seed={name}&backgroundColor=random"
_IMG = "https://placehold.co/400x300/png?text={label}"


def _avatar(name: str) -> str:
    return _AVA.format(name=name.replace(" ", "+"))


def _img(label: str) -> str:
    return _IMG.format(label=label.replace(" ", "+"))


def _ago(**kwargs) -> datetime:
    """Return a datetime in the past."""
    return datetime.utcnow() - timedelta(**kwargs)


def _in(**kwargs) -> datetime:
    """Return a datetime in the future."""
    return datetime.utcnow() + timedelta(**kwargs)


def seed_test_data(session: Session):
    """Seed database with realistic demo data that makes the app feel alive."""

    existing = session.exec(select(User).where(User.username == "owner1")).first()
    if existing:
        print("Test data already seeded")
        return

    print("Creating demo data...")

    # ========== USERS ==========

    owner = User(email="james@autocare.com", username="owner1",
                 hashed_password=get_password_hash("owner123"),
                 full_name="James Wilson", roles="user", is_active=True,
                 profile_image_url=_avatar("James Wilson"))
    owner2 = User(email="sarah@speedfix.com", username="owner2",
                  hashed_password=get_password_hash("owner123"),
                  full_name="Sarah Chen", roles="user", is_active=True,
                  profile_image_url=_avatar("Sarah Chen"))
    mechanic1 = User(email="mike@autocare.com", username="mechanic1",
                     hashed_password=get_password_hash("mechanic123"),
                     full_name="Mike Johnson", roles="user", is_active=True,
                     profile_image_url=_avatar("Mike Johnson"))
    mechanic2 = User(email="dave@autocare.com", username="mechanic2",
                     hashed_password=get_password_hash("mechanic123"),
                     full_name="Dave Martinez", roles="user", is_active=True,
                     profile_image_url=_avatar("Dave Martinez"))
    mechanic3 = User(email="lisa@speedfix.com", username="mechanic3",
                     hashed_password=get_password_hash("mechanic123"),
                     full_name="Lisa Park", roles="user", is_active=True,
                     profile_image_url=_avatar("Lisa Park"))
    customer1 = User(email="alex@gmail.com", username="customer1",
                     hashed_password=get_password_hash("customer123"),
                     full_name="Alex Thompson", roles="user", is_active=True,
                     profile_image_url=_avatar("Alex Thompson"))
    customer2 = User(email="maria@gmail.com", username="customer2",
                     hashed_password=get_password_hash("customer123"),
                     full_name="Maria Garcia", roles="user", is_active=True,
                     profile_image_url=_avatar("Maria Garcia"))
    customer3 = User(email="john@gmail.com", username="customer3",
                     hashed_password=get_password_hash("customer123"),
                     full_name="John Smith", roles="user", is_active=True,
                     profile_image_url=_avatar("John Smith"))
    # customer4 — no avatar yet, perfect for profile-edit demo
    customer4 = User(email="priya@gmail.com", username="customer4",
                     hashed_password=get_password_hash("customer123"),
                     full_name="Priya Patel", roles="user", is_active=True,
                     profile_image_url=None)

    for u in [owner, owner2, mechanic1, mechanic2, mechanic3,
              customer1, customer2, customer3, customer4]:
        session.add(u)
    session.flush()
    print("✓ Created 9 users")

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
        (owner.id,     shop1.id, ShopRole.OWNER),
        (mechanic1.id, shop1.id, ShopRole.MECHANIC),
        (mechanic2.id, shop1.id, ShopRole.MECHANIC),
        (owner2.id,    shop2.id, ShopRole.OWNER),
        (mechanic3.id, shop2.id, ShopRole.MECHANIC),
    ]:
        session.add(UserShop(user_id=user_id, shop_id=shop_id, role=role))
    session.flush()
    print("✓ Created 2 shops")

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

    # ========== PRODUCTS ==========

    products = [
        Product(shop_id=shop1.id, category_id=oil_cat.id,
                name="Mobil 1 Synthetic 5W-30 (5qt)",
                description="Full synthetic motor oil for high-performance engines",
                price=34.99, cost=22.00, stock_quantity=80,
                sku="OIL-M1-5W30", is_active=True,
                image_url=_img("Mobil+1+5W-30")),
        Product(shop_id=shop1.id, category_id=oil_cat.id,
                name="Castrol GTX 10W-40 (5qt)",
                description="Conventional oil, ideal for older vehicles",
                price=24.99, cost=14.00, stock_quantity=60,
                sku="OIL-GTX-10W40", is_active=True,
                image_url=_img("Castrol+GTX")),
        Product(shop_id=shop1.id, category_id=brake_cat.id,
                name="Bosch QuietCast Brake Pads (Front)",
                description="Ceramic pads with anti-squeal shims",
                price=54.99, cost=32.00, stock_quantity=25,
                sku="BRAKE-BQ-FRONT", is_active=True,
                image_url=_img("Brake+Pads+Front")),
        Product(shop_id=shop1.id, category_id=brake_cat.id,
                name="Bosch QuietCast Brake Pads (Rear)",
                description="Ceramic rear brake pads",
                price=44.99, cost=26.00, stock_quantity=20,
                sku="BRAKE-BQ-REAR", is_active=True,
                image_url=_img("Brake+Pads+Rear")),
        Product(shop_id=shop1.id, category_id=filter_cat.id,
                name="K&N High-Performance Air Filter",
                description="Washable, reusable performance air filter",
                price=49.99, cost=28.00, stock_quantity=15,
                sku="FILTER-KN-AIR", is_active=True,
                image_url=_img("K%26N+Air+Filter")),
        Product(shop_id=shop1.id, category_id=filter_cat.id,
                name="OEM Oil Filter",
                description="Standard replacement oil filter, universal fit",
                price=8.99, cost=3.50, stock_quantity=100,
                sku="FILTER-OIL-OEM", is_active=True,
                image_url=_img("Oil+Filter")),
        Product(shop_id=shop1.id, category_id=battery_cat.id,
                name="DieHard Platinum Battery (Group 35)",
                description="AGM battery, 3-year free replacement warranty",
                price=189.99, cost=110.00, stock_quantity=10,
                sku="BATT-DH-GRP35", is_active=True,
                image_url=_img("Car+Battery")),
        Product(shop_id=shop1.id, category_id=tire_cat.id,
                name="Michelin Pilot Sport 4 (225/45R17)",
                description="Ultra-high performance summer tire",
                price=179.99, cost=115.00, stock_quantity=12,
                sku="TIRE-MPS4-225", is_active=True,
                image_url=_img("Michelin+Tire")),
    ]
    products2 = [
        Product(shop_id=shop2.id, category_id=oil_cat.id,
                name="Valvoline MaxLife 5W-30 (5qt)",
                description="High-mileage oil with seal conditioners for engines over 75k miles",
                price=29.99, cost=18.00, stock_quantity=50,
                sku="OIL-VML-5W30", is_active=True,
                image_url=_img("Valvoline+MaxLife")),
        Product(shop_id=shop2.id, category_id=brake_cat.id,
                name="Wagner ThermoQuiet Brake Pads",
                description="Integrally moulded pads — no shims needed",
                price=39.99, cost=22.00, stock_quantity=30,
                sku="BRAKE-WTQ-FRONT", is_active=True,
                image_url=_img("Wagner+Brake+Pads")),
        Product(shop_id=shop2.id, category_id=battery_cat.id,
                name="Odyssey PC925 AGM Battery",
                description="Military-grade AGM, 400 cold-cranking amps",
                price=219.99, cost=140.00, stock_quantity=8,
                sku="BATT-OPC925", is_active=True,
                image_url=_img("Odyssey+Battery")),
        Product(shop_id=shop2.id, category_id=filter_cat.id,
                name="FRAM Extra Guard Oil Filter",
                description="Traps 95% of dirt particles down to 20 microns",
                price=6.99, cost=2.50, stock_quantity=120,
                sku="FILTER-FRAM-OIL", is_active=True,
                image_url=_img("FRAM+Oil+Filter")),
    ]
    for p in products + products2:
        session.add(p)
    session.flush()
    p_oil, p_oil2, p_brake_f, p_brake_r, p_air, p_oilfilter, p_battery, p_tire = products
    print(f"✓ Created {len(products) + len(products2)} products")

    # ========== SERVICES ==========

    services = [
        Service(shop_id=shop1.id, name="Full Oil Change",
                description="Drain & replace oil + filter, top up fluids, 21-point inspection",
                price=49.99, duration_minutes=30, service_type="shop_based", is_active=True,
                image_url=_img("Oil+Change")),
        Service(shop_id=shop1.id, name="Brake Pad Replacement",
                description="Replace front or rear brake pads, inspect rotors and callipers",
                price=149.99, duration_minutes=90, service_type="shop_based", is_active=True,
                image_url=_img("Brake+Replacement")),
        Service(shop_id=shop1.id, name="Full Brake Service",
                description="All 4 brake pads replaced, rotors machined/replaced, fluid bled",
                price=349.99, duration_minutes=180, service_type="shop_based", is_active=True,
                image_url=_img("Full+Brake+Service")),
        Service(shop_id=shop1.id, name="Battery Replacement",
                description="Battery load test + install new battery, reset electronics",
                price=39.99, duration_minutes=30, service_type="shop_based", is_active=True,
                image_url=_img("Battery+Replacement")),
        Service(shop_id=shop1.id, name="Tire Rotation & Balance",
                description="Rotate all 4 tires and dynamically balance each wheel",
                price=59.99, duration_minutes=60, service_type="shop_based", is_active=True,
                image_url=_img("Tire+Rotation")),
        Service(shop_id=shop1.id, name="Mobile Oil Change",
                description="We come to your home or office — full oil change on-site",
                price=69.99, duration_minutes=45, service_type="mobile",
                mobile_service_fee=20.00, is_active=True,
                image_url=_img("Mobile+Oil+Change")),
        Service(shop_id=shop1.id, name="Full Vehicle Inspection",
                description="50-point inspection with written report and photo evidence",
                price=89.99, duration_minutes=90, service_type="shop_based", is_active=True,
                image_url=_img("Vehicle+Inspection")),
    ]
    services2 = [
        Service(shop_id=shop2.id, name="Express Oil Change",
                description="15-minute oil change with no appointment required",
                price=39.99, duration_minutes=15, service_type="shop_based", is_active=True,
                image_url=_img("Express+Oil+Change")),
        Service(shop_id=shop2.id, name="Wheel Alignment",
                description="4-wheel computer alignment, printout provided",
                price=79.99, duration_minutes=60, service_type="shop_based", is_active=True,
                image_url=_img("Wheel+Alignment")),
        Service(shop_id=shop2.id, name="AC Recharge",
                description="Evacuate and recharge A/C system with R-134a refrigerant",
                price=119.99, duration_minutes=60, service_type="shop_based", is_active=True,
                image_url=_img("AC+Recharge")),
        Service(shop_id=shop2.id, name="Mobile Tyre Change",
                description="Roadside tyre change — we come to you 24/7",
                price=59.99, duration_minutes=30, service_type="mobile",
                mobile_service_fee=15.00, is_active=True,
                image_url=_img("Mobile+Tyre+Change")),
    ]
    for s in services + services2:
        session.add(s)
    session.flush()
    svc_oil, svc_brake, svc_full_brake, svc_battery, svc_tire, svc_mobile, svc_inspect = services
    svc2_express, svc2_align, svc2_ac, svc2_mobile_tyre = services2
    print(f"✓ Created {len(services) + len(services2)} services")

    # ========== APPOINTMENTS ==========

    appt_rows = [
        # ── COMPLETED (past) ──────────────────────────────────────────────
        Appointment(shop_id=shop1.id, customer_id=customer1.id, service_id=svc_oil.id,
                    vehicle_info="Toyota Camry 2021",
                    appointment_date=_ago(days=45),
                    status=AppointmentStatus.COMPLETED,
                    service_price=49.99, tax_amount=5.00, total_amount=54.99,
                    notes="Regular maintenance visit"),
        Appointment(shop_id=shop1.id, customer_id=customer2.id, service_id=svc_brake.id,
                    vehicle_info="Honda Civic 2019",
                    appointment_date=_ago(days=30),
                    status=AppointmentStatus.COMPLETED,
                    service_price=149.99, tax_amount=15.00, total_amount=164.99,
                    notes="Front brakes worn to 10%, urgent replacement"),
        Appointment(shop_id=shop1.id, customer_id=customer3.id, service_id=svc_inspect.id,
                    vehicle_info="Ford F-150 2022",
                    appointment_date=_ago(days=14),
                    status=AppointmentStatus.COMPLETED,
                    service_price=89.99, tax_amount=9.00, total_amount=98.99,
                    notes="Pre-purchase inspection for used vehicle"),
        Appointment(shop_id=shop1.id, customer_id=customer1.id, service_id=svc_tire.id,
                    vehicle_info="Toyota Camry 2021",
                    appointment_date=_ago(days=7),
                    status=AppointmentStatus.COMPLETED,
                    service_price=59.99, tax_amount=6.00, total_amount=65.99,
                    notes="Seasonal rotation"),
        # ── IN PROGRESS (today — Mike is actively working on Maria's Civic) ──
        Appointment(shop_id=shop1.id, customer_id=customer2.id, service_id=svc_full_brake.id,
                    vehicle_info="Honda Civic 2019",
                    appointment_date=_ago(hours=2),
                    status=AppointmentStatus.IN_PROGRESS,
                    service_price=349.99, tax_amount=35.00, total_amount=384.99,
                    notes="Full brake overhaul, customer waiting in lobby"),
        # ── CONFIRMED (upcoming) ─────────────────────────────────────────
        Appointment(shop_id=shop1.id, customer_id=customer3.id, service_id=svc_oil.id,
                    vehicle_info="Ford F-150 2022",
                    appointment_date=_in(days=2),
                    status=AppointmentStatus.CONFIRMED,
                    service_price=49.99, tax_amount=5.00, total_amount=54.99,
                    notes=""),
        Appointment(shop_id=shop1.id, customer_id=customer1.id, service_id=svc_battery.id,
                    vehicle_info="Toyota Camry 2021",
                    appointment_date=_in(days=3),
                    status=AppointmentStatus.CONFIRMED,
                    service_price=39.99, tax_amount=4.00, total_amount=43.99,
                    notes="Battery showing low voltage on cold mornings"),
        # ── PENDING (awaiting shop confirmation) ─────────────────────────
        Appointment(shop_id=shop1.id, customer_id=customer2.id, service_id=svc_mobile.id,
                    vehicle_info="Honda Civic 2019",
                    appointment_date=_in(days=5),
                    status=AppointmentStatus.PENDING,
                    service_price=69.99, mobile_service_fee=20.00,
                    tax_amount=9.00, total_amount=98.99,
                    notes="Home address: 42 Oak Street, please call before arriving"),
        Appointment(shop_id=shop1.id, customer_id=customer3.id, service_id=svc_inspect.id,
                    vehicle_info="Toyota RAV4 2020",
                    appointment_date=_in(days=6),
                    status=AppointmentStatus.PENDING,
                    service_price=89.99, tax_amount=9.00, total_amount=98.99,
                    notes="Buying this car — need a thorough 50-point inspection"),
        # ── CANCELLED ────────────────────────────────────────────────────
        Appointment(shop_id=shop1.id, customer_id=customer4.id, service_id=svc_oil.id,
                    vehicle_info="Nissan Altima 2018",
                    appointment_date=_ago(days=3),
                    status=AppointmentStatus.CANCELLED,
                    service_price=49.99, tax_amount=5.00, total_amount=54.99,
                    notes="Customer rescheduled due to work conflict"),
        # ── REJECTED (demonstrates the P0-2 fix) ─────────────────────────
        Appointment(shop_id=shop1.id, customer_id=customer4.id, service_id=svc_full_brake.id,
                    vehicle_info="Nissan Altima 2018",
                    appointment_date=_in(days=1),
                    status=AppointmentStatus.REJECTED,
                    service_price=349.99, tax_amount=35.00, total_amount=384.99,
                    notes="Slot unavailable — shop fully booked. Please rebook for next week."),
    ]
    for a in appt_rows:
        session.add(a)
    session.flush()

    completed = [a for a in appt_rows if a.status == AppointmentStatus.COMPLETED]
    appt_inprogress = appt_rows[4]   # Maria's Full Brake Service
    appt_rav4_inspect = appt_rows[8] # John's pending RAV4 inspection

    # SpeedFix appointments
    appt_shop2 = [
        Appointment(shop_id=shop2.id, customer_id=customer1.id, service_id=svc2_express.id,
                    vehicle_info="Toyota Camry 2021",
                    appointment_date=_ago(days=10),
                    status=AppointmentStatus.COMPLETED,
                    service_price=39.99, tax_amount=4.00, total_amount=43.99,
                    notes="Express oil change while waiting"),
        Appointment(shop_id=shop2.id, customer_id=customer3.id, service_id=svc2_align.id,
                    vehicle_info="Ford F-150 2022",
                    appointment_date=_in(days=4),
                    status=AppointmentStatus.CONFIRMED,
                    service_price=79.99, tax_amount=8.00, total_amount=87.99,
                    notes=""),
        Appointment(shop_id=shop2.id, customer_id=customer2.id, service_id=svc2_ac.id,
                    vehicle_info="Honda Civic 2019",
                    appointment_date=_in(days=7),
                    status=AppointmentStatus.PENDING,
                    service_price=119.99, tax_amount=12.00, total_amount=131.99,
                    notes="AC barely cooling — needs immediate recharge"),
    ]
    for a in appt_shop2:
        session.add(a)
    session.flush()

    completed_shop2 = [a for a in appt_shop2 if a.status == AppointmentStatus.COMPLETED]
    all_completed = completed + completed_shop2
    print(f"✓ Created {len(appt_rows) + len(appt_shop2)} appointments")

    # ========== SERVICE HISTORY ==========

    for appt in all_completed:
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

    # ========== INVOICES ==========

    for i, appt in enumerate(all_completed, start=1):
        inv = Invoice(
            shop_id=appt.shop_id,
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
    print(f"✓ Created {len(all_completed)} invoices (all paid)")

    # ========== PRODUCT ORDERS ==========

    orders_spec = [
        dict(customer_id=customer1.id, shop_id=shop1.id, status="completed",
             total_amount=p_oil.price + p_oilfilter.price,
             pickup_date=_ago(days=20), notes="",
             items=[(p_oil, 1), (p_oilfilter, 1)]),
        dict(customer_id=customer2.id, shop_id=shop1.id, status="ready",
             total_amount=p_brake_f.price,
             pickup_date=_in(days=1), notes="Call when ready for pickup",
             items=[(p_brake_f, 1)]),
        dict(customer_id=customer3.id, shop_id=shop1.id, status="pending",
             total_amount=p_oil.price * 2,
             pickup_date=_in(days=4), notes="",
             items=[(p_oil, 2)]),
        dict(customer_id=customer4.id, shop_id=shop2.id, status="confirmed",
             total_amount=products2[0].price,
             pickup_date=_in(days=2), notes="Pick up after 5 pm",
             items=[(products2[0], 1)]),
    ]
    orders = []
    for spec in orders_spec:
        order = ProductOrder(
            shop_id=spec["shop_id"],
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
        (svc_oil.id,     customer1.id, appt_rows[0].id, 5,
         "Quick and professional — oil change done in under 30 minutes. Will come back!"),
        (svc_brake.id,   customer2.id, appt_rows[1].id, 5,
         "Excellent work. Brakes feel brand new. Highly recommend AutoCare Pro!"),
        (svc_inspect.id, customer3.id, appt_rows[2].id, 4,
         "Very thorough inspection with a clear written report. Great value for money."),
        (svc_tire.id,    customer1.id, appt_rows[3].id, 5,
         "They noticed my front tires wearing unevenly and rotated accordingly. Saved money!"),
        (svc2_express.id, customer1.id, appt_shop2[0].id, 4,
         "In and out in 12 minutes. Fastest oil change I've ever had."),
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

    # ─────────────────────────────────────────────────────────────────────────
    # FROM HERE ON: data that makes the app feel like real users are active
    # ─────────────────────────────────────────────────────────────────────────

    # ========== CUSTOMER VEHICLES (My Garage) ==========
    # Each customer has their car(s) registered so "My Vehicles" page isn't empty.

    vehicles = [
        # Alex — 2 cars
        CustomerVehicle(customer_id=customer1.id, make="Toyota", model="Camry", year=2021,
                        engine="2.5L 4-Cylinder", fuel_type="gasoline",
                        transmission="automatic", license_plate="ABC-1234",
                        color="Silver", nickname="My Camry", is_primary=True),
        CustomerVehicle(customer_id=customer1.id, make="Honda", model="Accord", year=2018,
                        engine="1.5L Turbo", fuel_type="gasoline",
                        transmission="automatic", license_plate="ABC-5678",
                        color="Blue", nickname="Wife's Accord", is_primary=False),
        # Maria — 1 car
        CustomerVehicle(customer_id=customer2.id, make="Honda", model="Civic", year=2019,
                        engine="1.5L Turbo", fuel_type="gasoline",
                        transmission="CVT", license_plate="DEF-4567",
                        color="Red", nickname="Red Civic", is_primary=True),
        # John — 2 cars
        CustomerVehicle(customer_id=customer3.id, make="Ford", model="F-150", year=2022,
                        engine="3.5L EcoBoost V6", fuel_type="gasoline",
                        transmission="automatic", license_plate="GHI-7890",
                        color="Midnight Black", nickname="The Truck", is_primary=True),
        CustomerVehicle(customer_id=customer3.id, make="Toyota", model="RAV4", year=2020,
                        engine="2.5L Hybrid", fuel_type="hybrid",
                        transmission="CVT", license_plate="GHI-0123",
                        color="Pearl White", nickname="RAV4 (pre-purchase)", is_primary=False),
        # Priya — 1 car
        CustomerVehicle(customer_id=customer4.id, make="Nissan", model="Altima", year=2018,
                        engine="2.5L 4-Cylinder", fuel_type="gasoline",
                        transmission="CVT", license_plate="JKL-0124",
                        color="Gun Metal Gray", nickname="My Altima", is_primary=True),
    ]
    for v in vehicles:
        session.add(v)
    session.flush()
    print(f"✓ Created {len(vehicles)} customer vehicles")

    # ========== REPAIR PROGRESS ==========
    # Mike (mechanic1) is actively working on Maria's Full Brake Service right now.
    # The progress updates show the journey: received → diagnosing → in_progress.

    rp = RepairProgress(
        shop_id=shop1.id,
        customer_id=customer2.id,
        appointment_id=appt_inprogress.id,
        stage=RepairStage.IN_PROGRESS,
        description="Full brake overhaul — Honda Civic 2019",
        notes="Both front and rear rotors are in good shape. No replacement needed — saving the customer money.",
        estimated_completion=_in(hours=1, minutes=30),
        created_at=_ago(hours=1, minutes=50),
    )
    session.add(rp)
    session.flush()

    repair_updates = [
        RepairProgressUpdate(
            repair_progress_id=rp.id, updated_by=mechanic1.id,
            from_stage=None, to_stage=RepairStage.RECEIVED,
            note="Vehicle checked in. Assigned to Mike Johnson.",
            created_at=_ago(hours=1, minutes=50),
        ),
        RepairProgressUpdate(
            repair_progress_id=rp.id, updated_by=mechanic1.id,
            from_stage=RepairStage.RECEIVED, to_stage=RepairStage.DIAGNOSING,
            note="Lifting vehicle, inspecting all four brake assemblies.",
            created_at=_ago(hours=1, minutes=35),
        ),
        RepairProgressUpdate(
            repair_progress_id=rp.id, updated_by=mechanic1.id,
            from_stage=RepairStage.DIAGNOSING, to_stage=RepairStage.IN_PROGRESS,
            note="Diagnosis complete. Starting brake pad removal. Rotors look good — no machining needed.",
            created_at=_ago(hours=1),
        ),
    ]
    for u in repair_updates:
        session.add(u)
    session.flush()
    print("✓ Created repair progress (Maria's brake service — 3 stage updates)")

    # ========== QUOTATIONS ==========

    # Quotation 1: APPROVED — for Maria's Full Brake Service (in-progress)
    # The shop sent this quote and Maria approved it before the work started.
    quot_brake = Quotation(
        shop_id=shop1.id,
        customer_id=customer2.id,
        appointment_id=appt_inprogress.id,
        status=QuotationStatus.APPROVED,
        title="Full Brake Service — Honda Civic 2019",
        description="Complete brake overhaul: all four pads + rotor inspection. Includes labour and parts.",
        labor_cost=200.00,
        parts_cost=109.98,
        tax_amount=31.00,
        discount_amount=0.00,
        total_amount=340.98,
        valid_until=_in(days=7),
        approved_at=_ago(hours=3),
        created_at=_ago(days=1),
    )
    session.add(quot_brake)
    session.flush()
    for item in [
        QuotationItem(quotation_id=quot_brake.id, item_type="labor",
                      name="Brake Service Labour", quantity=1.0,
                      unit_price=200.00, total_price=200.00),
        QuotationItem(quotation_id=quot_brake.id, item_type="part",
                      name="Bosch QuietCast Brake Pads (Front)",
                      quantity=1.0, unit_price=54.99, total_price=54.99),
        QuotationItem(quotation_id=quot_brake.id, item_type="part",
                      name="Bosch QuietCast Brake Pads (Rear)",
                      quantity=1.0, unit_price=44.99, total_price=44.99),
        QuotationItem(quotation_id=quot_brake.id, item_type="tax",
                      name="Tax (10%)", quantity=1.0, unit_price=31.00, total_price=31.00),
    ]:
        session.add(item)

    # Quotation 2: SENT (awaiting decision) — John's RAV4 inspection + expected extras
    quot_inspect = Quotation(
        shop_id=shop1.id,
        customer_id=customer3.id,
        appointment_id=appt_rav4_inspect.id,
        status=QuotationStatus.SENT,
        title="Pre-Purchase Inspection — Toyota RAV4 2020",
        description="Full 50-point inspection. Based on the vehicle age, we recommend also running a diagnostic scan and checking all fluids.",
        labor_cost=89.99,
        parts_cost=0.00,
        tax_amount=9.00,
        discount_amount=0.00,
        total_amount=98.99,
        valid_until=_in(days=5),
        created_at=_ago(hours=18),
    )
    session.add(quot_inspect)
    session.flush()
    for item in [
        QuotationItem(quotation_id=quot_inspect.id, item_type="service",
                      name="50-Point Vehicle Inspection",
                      quantity=1.0, unit_price=89.99, total_price=89.99),
        QuotationItem(quotation_id=quot_inspect.id, item_type="service",
                      name="OBD Diagnostic Scan (complimentary)",
                      quantity=1.0, unit_price=0.00, total_price=0.00),
        QuotationItem(quotation_id=quot_inspect.id, item_type="tax",
                      name="Tax (10%)", quantity=1.0, unit_price=9.00, total_price=9.00),
    ]:
        session.add(item)

    # Quotation 3: SENT — Engine mount check for Alex (found during tire rotation last week)
    quot_engine = Quotation(
        shop_id=shop1.id,
        customer_id=customer1.id,
        appointment_id=None,
        status=QuotationStatus.SENT,
        title="Engine Mount Inspection & Replacement",
        description="During your last tire rotation we noticed a slight vibration that may indicate a worn engine mount. Recommend inspection before it worsens.",
        labor_cost=120.00,
        parts_cost=85.00,
        tax_amount=20.50,
        discount_amount=10.00,
        total_amount=215.50,
        valid_until=_in(days=10),
        created_at=_ago(days=5),
    )
    session.add(quot_engine)
    session.flush()
    for item in [
        QuotationItem(quotation_id=quot_engine.id, item_type="labor",
                      name="Engine Mount Inspection & Replacement Labour",
                      quantity=1.0, unit_price=120.00, total_price=120.00),
        QuotationItem(quotation_id=quot_engine.id, item_type="part",
                      name="Genuine Engine Mount (OEM)",
                      quantity=1.0, unit_price=85.00, total_price=85.00),
        QuotationItem(quotation_id=quot_engine.id, item_type="discount",
                      name="Loyal Customer Discount",
                      quantity=1.0, unit_price=-10.00, total_price=-10.00),
        QuotationItem(quotation_id=quot_engine.id, item_type="tax",
                      name="Tax (10%)", quantity=1.0, unit_price=20.50, total_price=20.50),
    ]:
        session.add(item)
    session.flush()
    print("✓ Created 3 quotations (1 approved, 2 pending customer decision)")

    # ========== CHAT ROOMS + MESSAGES ==========
    # Realistic conversations between customers and shop staff.

    # ── Chat Room 1: Maria ↔ AutoCare Pro (about today's brake service) ──────
    room1 = ChatRoom(
        shop_id=shop1.id, customer_id=customer2.id,
        room_type=ChatRoomType.APPOINTMENT,
        appointment_id=appt_inprogress.id,
        is_active=True, created_at=_ago(hours=2, minutes=10),
    )
    session.add(room1)
    session.flush()

    room1_msgs = [
        ChatMessage(room_id=room1.id, sender_id=customer2.id,
                    content="Hi! Just leaving home now for my full brake service. Should arrive in about 15 minutes.",
                    is_read=True, created_at=_ago(hours=2, minutes=10)),
        ChatMessage(room_id=room1.id, sender_id=owner.id,
                    content="Hi Maria! We're expecting you. Mike will be your mechanic today — he's one of our best. Pull up to Bay 2.",
                    is_read=True, created_at=_ago(hours=2, minutes=5)),
        ChatMessage(room_id=room1.id, sender_id=customer2.id,
                    content="Perfect, see you soon! Quick question — approximately how long will it take?",
                    is_read=True, created_at=_ago(hours=1, minutes=55)),
        ChatMessage(room_id=room1.id, sender_id=mechanic1.id,
                    content="Hi Maria, I'm Mike! For a full brake service, plan for about 2.5–3 hours. We have a comfortable waiting area with Wi-Fi and coffee ☕",
                    is_read=True, created_at=_ago(hours=1, minutes=45)),
        ChatMessage(room_id=room1.id, sender_id=customer2.id,
                    content="Great, I'll wait there. Thank you!",
                    is_read=True, created_at=_ago(hours=1, minutes=40)),
        ChatMessage(room_id=room1.id, sender_id=mechanic1.id,
                    content="UPDATE: I've lifted the car and started inspection. Good news — both rotors look solid, no machining needed. This will save you about $80 on the original estimate!",
                    is_read=True, created_at=_ago(hours=1)),
        ChatMessage(room_id=room1.id, sender_id=customer2.id,
                    content="That's great news! Thank you for letting me know 🙌",
                    is_read=True, created_at=_ago(minutes=55)),
        # Latest message — unread by customer (she hasn't checked the app since)
        ChatMessage(room_id=room1.id, sender_id=mechanic1.id,
                    content="All four pads are replaced. Now bleeding the brake fluid and doing final checks. Should be done in about 30–40 minutes. I'll send another message when ready for pickup.",
                    is_read=False, created_at=_ago(minutes=20)),
    ]
    for m in room1_msgs:
        session.add(m)

    # ── Chat Room 2: John ↔ AutoCare Pro (about RAV4 pending inspection) ─────
    room2 = ChatRoom(
        shop_id=shop1.id, customer_id=customer3.id,
        room_type=ChatRoomType.APPOINTMENT,
        appointment_id=appt_rav4_inspect.id,
        is_active=True, created_at=_ago(days=1, hours=2),
    )
    session.add(room2)
    session.flush()

    room2_msgs = [
        ChatMessage(room_id=room2.id, sender_id=customer3.id,
                    content="Hi, I just submitted a booking request for a full vehicle inspection on a used RAV4 I'm thinking of buying. Can you confirm it was received?",
                    is_read=True, created_at=_ago(days=1, hours=2)),
        ChatMessage(room_id=room2.id, sender_id=owner.id,
                    content="Hi John! Yes, we received it — thank you. We'll confirm the appointment slot within a few hours.",
                    is_read=True, created_at=_ago(days=1, hours=1, minutes=45)),
        ChatMessage(room_id=room2.id, sender_id=customer3.id,
                    content="This is really important — I'm about to spend $22k on this car. I need a thorough check.",
                    is_read=True, created_at=_ago(days=1, hours=1, minutes=30)),
        ChatMessage(room_id=room2.id, sender_id=owner.id,
                    content="Understood, John. We take pre-purchase inspections very seriously. You'll get a 50-point written report with photos of anything we find. If there are issues, you'll know before signing anything.",
                    is_read=True, created_at=_ago(days=1, hours=1, minutes=15)),
        ChatMessage(room_id=room2.id, sender_id=customer3.id,
                    content="Perfect. Should I ask the seller to bring the car, or do I bring it?",
                    is_read=True, created_at=_ago(days=1, hours=1)),
        ChatMessage(room_id=room2.id, sender_id=owner.id,
                    content="Either works. We just need access to the vehicle for about 90 minutes. Having the seller present is optional but can speed things up if we have questions.",
                    is_read=True, created_at=_ago(days=1, minutes=50)),
        ChatMessage(room_id=room2.id, sender_id=customer3.id,
                    content="Got it, I'll come alone first. Thanks!",
                    is_read=True, created_at=_ago(days=1, minutes=40)),
        # Latest — unread by John (owner sent it while John was offline)
        ChatMessage(room_id=room2.id, sender_id=owner.id,
                    content="John, also check your app — we've sent over a quotation with the inspection breakdown. Your slot is still pending confirmation but we'll get back to you today.",
                    is_read=False, created_at=_ago(hours=6)),
    ]
    for m in room2_msgs:
        session.add(m)

    # ── Chat Room 3: Alex ↔ AutoCare Pro (follow-up after oil order) ──────────
    room3 = ChatRoom(
        shop_id=shop1.id, customer_id=customer1.id,
        room_type=ChatRoomType.GENERAL,
        is_active=True, created_at=_ago(days=5),
    )
    session.add(room3)
    session.flush()

    room3_msgs = [
        ChatMessage(room_id=room3.id, sender_id=customer1.id,
                    content="Hi team! Just wanted to say the Mobil 1 synthetic I ordered last month is fantastic — engine sounds so much smoother.",
                    is_read=True, created_at=_ago(days=5)),
        ChatMessage(room_id=room3.id, sender_id=owner.id,
                    content="That's great to hear, Alex! Mobil 1 full synthetic is worth every penny. We also have a Castrol Edge in stock if you ever want to compare.",
                    is_read=True, created_at=_ago(days=4, hours=23)),
        ChatMessage(room_id=room3.id, sender_id=customer1.id,
                    content="I'll stick with Mobil 1 for now! I also noticed my battery seems slow to crank on cold mornings — I booked a battery replacement for next week.",
                    is_read=True, created_at=_ago(days=4, hours=22)),
        ChatMessage(room_id=room3.id, sender_id=owner.id,
                    content="Good call getting it checked before winter. We'll run a full load test first — sometimes it just needs a terminal clean. Either way, you'll leave with a healthy battery.",
                    is_read=True, created_at=_ago(days=4, hours=21)),
        ChatMessage(room_id=room3.id, sender_id=customer1.id,
                    content="Also — we sent over a quote about an engine mount. Is that urgent?",
                    is_read=True, created_at=_ago(days=4, hours=20)),
        ChatMessage(room_id=room3.id, sender_id=mechanic1.id,
                    content="Hi Alex, Mike here. The mount isn't critical right now but I'd get it sorted in the next 2–3 months. If left too long it puts stress on the transmission. The quote has a loyal customer discount already applied.",
                    is_read=True, created_at=_ago(days=4, hours=19)),
        # Unread — Alex hasn't replied yet
        ChatMessage(room_id=room3.id, sender_id=owner.id,
                    content="No pressure at all, Alex. Take your time with the quote. See you next week for the battery! 🔋",
                    is_read=False, created_at=_ago(days=4, hours=18)),
    ]
    for m in room3_msgs:
        session.add(m)

    # ── Chat Room 4: Priya ↔ AutoCare Pro (after booking rejection) ───────────
    room4 = ChatRoom(
        shop_id=shop1.id, customer_id=customer4.id,
        room_type=ChatRoomType.GENERAL,
        is_active=True, created_at=_ago(days=1),
    )
    session.add(room4)
    session.flush()

    room4_msgs = [
        ChatMessage(room_id=room4.id, sender_id=customer4.id,
                    content="Hi, I just received a rejection for my Full Brake Service booking. Can you explain why?",
                    is_read=True, created_at=_ago(days=1)),
        ChatMessage(room_id=room4.id, sender_id=owner.id,
                    content="Hi Priya, so sorry about that! We had an emergency booking come in that took our last available Bay 3 slot. Your requested time was no longer available.",
                    is_read=True, created_at=_ago(hours=23)),
        ChatMessage(room_id=room4.id, sender_id=customer4.id,
                    content="I see. When is the next available slot?",
                    is_read=True, created_at=_ago(hours=22, minutes=30)),
        ChatMessage(room_id=room4.id, sender_id=owner.id,
                    content="We have openings next Tuesday at 10 AM or Thursday at 2 PM. Both work for a Full Brake Service. Would either of those suit you?",
                    is_read=True, created_at=_ago(hours=22)),
        # Unread — Priya hasn't responded yet
        ChatMessage(room_id=room4.id, sender_id=owner.id,
                    content="Just following up, Priya — let us know which slot works and we'll confirm it immediately. We'll also apply a 5% courtesy discount for the inconvenience.",
                    is_read=False, created_at=_ago(hours=4)),
    ]
    for m in room4_msgs:
        session.add(m)

    session.flush()
    print("✓ Created 4 chat rooms with 28 messages (realistic ongoing conversations)")

    # ========== NOTIFICATIONS ==========
    # Inbox entries so every user sees something when they open the app.

    notifications = [
        # customer1 (Alex) — unread quote + confirmed booking
        Notification(
            user_id=customer1.id,
            type=NotificationType.STATUS_UPDATE,
            title="New Estimate from AutoCare Pro",
            message="AutoCare Pro has sent you a quote for Engine Mount Inspection & Replacement ($215.50). Tap to review.",
            status=NotificationStatus.UNREAD,
            appointment_id=None,
            created_at=_ago(days=5),
        ),
        Notification(
            user_id=customer1.id,
            type=NotificationType.BOOKING_CONFIRMED,
            title="Battery Replacement Confirmed ✓",
            message="Your battery replacement appointment at AutoCare Pro has been confirmed. See you in 3 days!",
            status=NotificationStatus.UNREAD,
            appointment_id=appt_rows[6].id,
            created_at=_ago(days=1),
        ),
        Notification(
            user_id=customer1.id,
            type=NotificationType.ORDER_READY,
            title="Your oil order is ready — SpeedFix",
            message="Order #ORD-001 is ready for pickup at SpeedFix Garage. Open until 6 PM.",
            status=NotificationStatus.READ,
            product_order_id=orders[0].id,
            created_at=_ago(days=20),
        ),
        # customer2 (Maria) — active repair updates
        Notification(
            user_id=customer2.id,
            type=NotificationType.BOOKING_CONFIRMED,
            title="Full Brake Service Confirmed ✓",
            message="Your full brake service appointment today at AutoCare Pro is confirmed. Drop off at Bay 2.",
            status=NotificationStatus.READ,
            appointment_id=appt_inprogress.id,
            created_at=_ago(days=1),
        ),
        Notification(
            user_id=customer2.id,
            type=NotificationType.STATUS_UPDATE,
            title="Repair In Progress 🔧",
            message="Mike has started working on your Honda Civic. Estimated completion: 1.5 hours. Check the chat for updates.",
            status=NotificationStatus.UNREAD,
            appointment_id=appt_inprogress.id,
            created_at=_ago(hours=1),
        ),
        Notification(
            user_id=customer2.id,
            type=NotificationType.ORDER_READY,
            title="Your Brake Pads Are Ready for Pickup",
            message="Your front brake pad order at AutoCare Pro is ready. Swing by anytime today.",
            status=NotificationStatus.UNREAD,
            product_order_id=orders[1].id,
            created_at=_ago(hours=3),
        ),
        # customer3 (John) — quotation + chat message
        Notification(
            user_id=customer3.id,
            type=NotificationType.STATUS_UPDATE,
            title="Inspection Quote Ready",
            message="AutoCare Pro has sent you a quote for your RAV4 pre-purchase inspection ($98.99). Approve to confirm your slot.",
            status=NotificationStatus.UNREAD,
            appointment_id=appt_rav4_inspect.id,
            created_at=_ago(hours=18),
        ),
        Notification(
            user_id=customer3.id,
            type=NotificationType.REMINDER,
            title="Upcoming: Wheel Alignment at SpeedFix",
            message="Reminder: your wheel alignment at SpeedFix Garage is in 4 days. Reply to reschedule.",
            status=NotificationStatus.UNREAD,
            appointment_id=appt_shop2[1].id,
            created_at=_ago(hours=2),
        ),
        # customer4 (Priya) — rejection + follow-up
        Notification(
            user_id=customer4.id,
            type=NotificationType.BOOKING_REJECTED,
            title="Booking Request Declined",
            message="AutoCare Pro couldn't accommodate your Full Brake Service for tomorrow. Open the chat to rebook — they have slots next Tuesday & Thursday.",
            status=NotificationStatus.READ,
            appointment_id=appt_rows[10].id,
            created_at=_ago(days=1),
        ),
        Notification(
            user_id=customer4.id,
            type=NotificationType.BOOKING_CANCELLED,
            title="Your Oil Change Was Cancelled",
            message="Your oil change booking 3 days ago was cancelled at your request. Book a new slot anytime.",
            status=NotificationStatus.READ,
            appointment_id=appt_rows[9].id,
            created_at=_ago(days=3),
        ),
        # owner1 (James) — pending bookings need attention
        Notification(
            user_id=owner.id,
            type=NotificationType.NEW_BOOKING,
            title="New Booking Request 📋",
            message="Maria Garcia has requested a Mobile Oil Change for in 5 days. Tap to confirm or suggest an alternative slot.",
            status=NotificationStatus.UNREAD,
            appointment_id=appt_rows[7].id,
            created_at=_ago(days=1),
        ),
        Notification(
            user_id=owner.id,
            type=NotificationType.NEW_BOOKING,
            title="New Booking Request 📋",
            message="John Smith has requested a Full Vehicle Inspection (RAV4 2020) in 6 days. Confirmation pending.",
            status=NotificationStatus.UNREAD,
            appointment_id=appt_rav4_inspect.id,
            created_at=_ago(hours=18),
        ),
        # mechanic1 (Mike) — new job assigned
        Notification(
            user_id=mechanic1.id,
            type=NotificationType.NEW_BOOKING,
            title="Job Assigned: Full Brake Service",
            message="You've been assigned Maria Garcia's Full Brake Service (Honda Civic 2019). Customer is waiting in the lobby.",
            status=NotificationStatus.READ,
            appointment_id=appt_inprogress.id,
            created_at=_ago(hours=2),
        ),
    ]
    for n in notifications:
        session.add(n)
    session.flush()
    print(f"✓ Created {len(notifications)} notifications across all users")

    # ========== MECHANIC PERFORMANCE ==========
    # Records for completed services so the performance dashboard isn't empty.

    perf_records = [
        # Mike — oil change for Alex (45 days ago, rated 5★)
        MechanicPerformance(
            mechanic_id=mechanic1.id, shop_id=shop1.id,
            appointment_id=appt_rows[0].id,
            service_name="Full Oil Change — Toyota Camry 2021",
            completed_date=_ago(days=45),
            revenue_generated=54.99,
            service_rating=5,
            customer_feedback="Really quick, done in 25 minutes. Mike was professional and friendly.",
            estimated_duration=30, actual_duration=25,
        ),
        # Dave — brake pads for Maria (30 days ago, rated 5★)
        MechanicPerformance(
            mechanic_id=mechanic2.id, shop_id=shop1.id,
            appointment_id=appt_rows[1].id,
            service_name="Brake Pad Replacement — Honda Civic 2019",
            completed_date=_ago(days=30),
            revenue_generated=164.99,
            service_rating=5,
            customer_feedback="Dave was thorough and explained everything clearly. Will request him again.",
            estimated_duration=90, actual_duration=85,
        ),
        # Mike — inspection for John (14 days ago, rated 4★)
        MechanicPerformance(
            mechanic_id=mechanic1.id, shop_id=shop1.id,
            appointment_id=appt_rows[2].id,
            service_name="Full Vehicle Inspection — Ford F-150 2022",
            completed_date=_ago(days=14),
            revenue_generated=98.99,
            service_rating=4,
            customer_feedback="Very thorough report with photos. Slightly longer than quoted but worth it.",
            estimated_duration=90, actual_duration=110,
        ),
        # Dave — tire rotation for Alex (7 days ago, rated 5★)
        MechanicPerformance(
            mechanic_id=mechanic2.id, shop_id=shop1.id,
            appointment_id=appt_rows[3].id,
            service_name="Tire Rotation & Balance — Toyota Camry 2021",
            completed_date=_ago(days=7),
            revenue_generated=65.99,
            service_rating=5,
            customer_feedback="Great catch on the uneven wear — they saved me from buying new tires too early!",
            estimated_duration=60, actual_duration=55,
        ),
        # Lisa — express oil for Alex at SpeedFix (10 days ago, rated 4★)
        MechanicPerformance(
            mechanic_id=mechanic3.id, shop_id=shop2.id,
            appointment_id=appt_shop2[0].id,
            service_name="Express Oil Change — Toyota Camry 2021",
            completed_date=_ago(days=10),
            revenue_generated=43.99,
            service_rating=4,
            customer_feedback="Impressively fast. In and out in 12 minutes.",
            estimated_duration=15, actual_duration=12,
        ),
    ]
    for pr in perf_records:
        session.add(pr)

    # Mechanic ratings (linked to completed appointments)
    mechanic_ratings = [
        MechanicRating(mechanic_id=mechanic1.id, customer_id=customer1.id,
                       appointment_id=appt_rows[0].id, rating=5,
                       review="Mike is awesome — super fast and explained the oil grade choice."),
        MechanicRating(mechanic_id=mechanic2.id, customer_id=customer2.id,
                       appointment_id=appt_rows[1].id, rating=5,
                       review="Dave replaced my brakes perfectly. Car feels like new."),
        MechanicRating(mechanic_id=mechanic1.id, customer_id=customer3.id,
                       appointment_id=appt_rows[2].id, rating=4,
                       review="Great inspection report. Took a bit longer than expected but quality was top-notch."),
        MechanicRating(mechanic_id=mechanic2.id, customer_id=customer1.id,
                       appointment_id=appt_rows[3].id, rating=5,
                       review="Dave noticed my tires wearing unevenly and fixed the rotation pattern. Excellent work."),
    ]
    for mr in mechanic_ratings:
        session.add(mr)

    session.flush()
    print(f"✓ Created {len(perf_records)} mechanic performance records + {len(mechanic_ratings)} mechanic ratings")

    session.commit()

    all_products_count = len(products) + len(products2)
    all_services_count = len(services) + len(services2)
    all_appts_count = len(appt_rows) + len(appt_shop2)
    total_messages = sum([len(room1_msgs), len(room2_msgs), len(room3_msgs), len(room4_msgs)])

    print("\n" + "=" * 68)
    print("  DEMO DATA READY — APP FEELS LIKE REAL USERS ARE ACTIVE")
    print("=" * 68)
    print("  Admin:      admin      / admin123")
    print("  Owner:      owner1     / owner123   (James Wilson — AutoCare Pro)")
    print("  Owner:      owner2     / owner123   (Sarah Chen  — SpeedFix)")
    print("  Mechanic:   mechanic1  / mechanic123  (Mike Johnson  — AutoCare Pro)")
    print("  Mechanic:   mechanic2  / mechanic123  (Dave Martinez — AutoCare Pro)")
    print("  Mechanic:   mechanic3  / mechanic123  (Lisa Park     — SpeedFix)")
    print("  Customer:   customer1  / customer123  (Alex Thompson — 2 cars, open quote)")
    print("  Customer:   customer2  / customer123  (Maria Garcia  — brake service IN PROGRESS right now)")
    print("  Customer:   customer3  / customer123  (John Smith    — pending inspection + unread quote)")
    print("  Customer:   customer4  / customer123  (Priya Patel   — rejected booking, no avatar)")
    print("=" * 68)
    print(f"  Shops:          AutoCare Pro (ID {shop1.id}), SpeedFix (ID {shop2.id})")
    print(f"  Products:       {all_products_count} (with image URLs)")
    print(f"  Services:       {all_services_count} (with image URLs)")
    print(f"  Appointments:   {all_appts_count} total — {len(all_completed)} completed, 1 in-progress,")
    print("                  1 rejected, 1 cancelled, rest upcoming")
    print(f"  Invoices:       {len(all_completed)} (all paid)")
    print(f"  Orders:         {len(orders)} (completed / ready / pending / confirmed)")
    print(f"  Vehicles:       {len(vehicles)} customer vehicles across 4 customers")
    print("  Repair Progress: 1 active (Maria's brake service — 3 stage updates)")
    print("  Quotations:     3 (1 approved, 2 awaiting customer decision)")
    print(f"  Chat Rooms:     4 rooms / {total_messages} messages (recent, realistic dialogue)")
    print(f"  Notifications:  {len(notifications)} (mix of unread + read across all users)")
    print(f"  Perf Records:   {len(perf_records)} mechanic records + {len(mechanic_ratings)} mechanic ratings")
    print("─" * 68)
    print("  LIVE ACTIVITY:")
    print("  • Maria's brake service is in-progress RIGHT NOW (chat is active)")
    print("  • John has an unread quote + unread chat message waiting")
    print("  • Alex has an unread estimate ($215.50) and an upcoming battery appt")
    print("  • Priya has a rejected booking — shop offered 5% discount to rebook")
    print("  • Owner (James) has 2 unread NEW_BOOKING notifications to confirm")
    print("=" * 68)
