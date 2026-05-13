"""Product Order endpoints for customer self-service purchases."""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, SQLModel

from app.db import get_session
from app.models.product_order import (
    ProductOrder, ProductOrderItem, ProductOrderCreate, ProductOrderRead,
    ProductOrderStatusUpdate, OrderStatus, ProductOrderItemCreate,
)
from app.models.shop import UserShop
from app.core.security import get_current_user, TokenData
from app.repositories.shop_repository import ShopRepository
from app.repositories.user_repository import UserRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.order_repository import OrderRepository
from app.services.shop_service import ShopService
from app.services.notification_service import NotificationService
from app.services.pricing_service import PricingService

router = APIRouter(prefix="/product-orders", tags=["product-orders"])


# ── Dependency factories ──────────────────────────────────────────────────────

def get_shop_service(session: Session = Depends(get_session)) -> ShopService:
    return ShopService(ShopRepository(session))


def get_notification_service(session: Session = Depends(get_session)) -> NotificationService:
    return NotificationService(
        NotificationRepository(session),
        ShopRepository(session),
        UserRepository(session),
    )


def get_pricing_service(session: Session = Depends(get_session)) -> PricingService:
    return PricingService(ProductRepository(session), OrderRepository(session))


def get_shop_repo(session: Session = Depends(get_session)) -> ShopRepository:
    return ShopRepository(session)


def get_user_repo(session: Session = Depends(get_session)) -> UserRepository:
    return UserRepository(session)


def get_order_repo(session: Session = Depends(get_session)) -> OrderRepository:
    return OrderRepository(session)


def get_product_repo(session: Session = Depends(get_session)) -> ProductRepository:
    return ProductRepository(session)


# ── Request models ────────────────────────────────────────────────────────────

class UnifiedBookingCreate(SQLModel):
    """Unified booking — can be service only, products only, or both."""
    shop_id: int
    customer_vehicle_id: Optional[int] = None
    vehicle_info: Optional[str] = None
<<<<<<< HEAD
    
    # Vehicle details (for auto-saving if customer_vehicle_id not provided)
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_year: Optional[int] = None
    vehicle_engine: Optional[str] = None
    vehicle_fuel_type: Optional[str] = None
    vehicle_license_plate: Optional[str] = None
    
    # Service info (optional - for service appointments)
=======

>>>>>>> 0d029f616eb7b0c534aa90153fa5c13416944b1b
    service_id: Optional[int] = None
    service_notes: Optional[str] = None
    appointment_date: Optional[datetime] = None

    product_items: Optional[List[ProductOrderItemCreate]] = []
    product_notes: Optional[str] = None

    pickup_date: Optional[datetime] = None
    customer_address: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_location_lat: Optional[float] = None
    customer_location_lng: Optional[float] = None
    notes: Optional[str] = None


# ── Unified booking ───────────────────────────────────────────────────────────

@router.post("/unified-booking", status_code=status.HTTP_201_CREATED)
def create_unified_booking(
    booking_data: UnifiedBookingCreate,
    current_user: TokenData = Depends(get_current_user),
    shop_repo: ShopRepository = Depends(get_shop_repo),
    product_repo: ProductRepository = Depends(get_product_repo),
    order_repo: OrderRepository = Depends(get_order_repo),
    notification_service: NotificationService = Depends(get_notification_service),
    pricing_service: PricingService = Depends(get_pricing_service),
    user_repo: UserRepository = Depends(get_user_repo),
):
    """Book service AND order products at the same time."""
    from app.models.appointment import Appointment, AppointmentStatus
    from app.models.customer_vehicle import CustomerVehicle
    from app.models.notification import NotificationType

    result = {"appointment": None, "product_order": None}

    # Ensure customer is associated with this shop
    user_shop = shop_repo.get_active_user_shop(current_user.user_id, booking_data.shop_id)
    if not user_shop:
        shop_repo.stage_user_shop(
            UserShop(user_id=current_user.user_id, shop_id=booking_data.shop_id, role="customer")
        )
<<<<<<< HEAD
        session.add(user_shop)
        session.flush()
    
    # Handle vehicle - validate existing or auto-save new
    customer_vehicle_id = booking_data.customer_vehicle_id
    
    if customer_vehicle_id:
        # Validate existing vehicle
        vehicle = session.exec(
=======

    # Validate customer vehicle if provided
    if booking_data.customer_vehicle_id:
        from sqlmodel import select
        vehicle = order_repo.session.exec(
>>>>>>> 0d029f616eb7b0c534aa90153fa5c13416944b1b
            select(CustomerVehicle).where(
                CustomerVehicle.id == customer_vehicle_id,
                CustomerVehicle.customer_id == current_user.user_id,
                CustomerVehicle.is_active,
            )
        ).first()
        if not vehicle:
<<<<<<< HEAD
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehicle not found"
            )
    elif booking_data.vehicle_make and booking_data.vehicle_model:
        # Auto-save new vehicle if make and model provided
        new_vehicle = CustomerVehicle(
            customer_id=current_user.user_id,
            make=booking_data.vehicle_make,
            model=booking_data.vehicle_model,
            year=booking_data.vehicle_year,
            engine=booking_data.vehicle_engine,
            fuel_type=booking_data.vehicle_fuel_type,
            license_plate=booking_data.vehicle_license_plate,
            is_active=True
        )
        session.add(new_vehicle)
        session.flush()
        customer_vehicle_id = new_vehicle.id
    
=======
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

>>>>>>> 0d029f616eb7b0c534aa90153fa5c13416944b1b
    # Calculate pricing
    price_calculation = pricing_service.calculate_appointment_price(
        service_id=booking_data.service_id,
        product_items=[item.model_dump() for item in (booking_data.product_items or [])],
        discount_amount=0.0,
    )

    # 1. Create service appointment (if service_id provided)
    if booking_data.service_id:
        from app.models.product import ServiceType
        service = product_repo.get_service(booking_data.service_id)

        appointment_notes = booking_data.service_notes or ""
        if booking_data.notes:
            appointment_notes += f"\n{booking_data.notes}"

        if service and service.service_type == ServiceType.MOBILE:
            location_info = "\n[MOBILE SERVICE]"
            if booking_data.customer_address:
                location_info += f"\nAddress: {booking_data.customer_address}"
            if booking_data.customer_phone:
                location_info += f"\nPhone: {booking_data.customer_phone}"
            if booking_data.customer_location_lat and booking_data.customer_location_lng:
                location_info += f"\nGPS: {booking_data.customer_location_lat}, {booking_data.customer_location_lng}"
            appointment_notes += location_info

        appointment = Appointment(
            shop_id=booking_data.shop_id,
            customer_id=current_user.user_id,
            service_id=booking_data.service_id,
            customer_vehicle_id=customer_vehicle_id,
            vehicle_info=booking_data.vehicle_info,
            appointment_date=booking_data.appointment_date or datetime.utcnow(),
            notes=appointment_notes.strip(),
            status=AppointmentStatus.PENDING,
            service_price=price_calculation["service_price"],
            mobile_service_fee=price_calculation["mobile_service_fee"],
            discount_amount=price_calculation["discount_amount"],
            tax_amount=price_calculation["tax_amount"],
            total_amount=price_calculation["total_amount"],
        )
        order_repo.add_pending(appointment)
        order_repo.flush()

        result["appointment"] = {
            "id": appointment.id,
            "service_id": appointment.service_id,
            "appointment_date": appointment.appointment_date,
            "status": appointment.status,
            "service_type": service.service_type if service else "shop_based",
            "pricing": {
                "service_price": appointment.service_price,
                "mobile_fee": appointment.mobile_service_fee,
                "discount": appointment.discount_amount,
                "tax": appointment.tax_amount,
                "total": appointment.total_amount,
            },
        }

    # 2. Create product order (if products provided)
    if booking_data.product_items:
        product_order = ProductOrder(
            shop_id=booking_data.shop_id,
            customer_id=current_user.user_id,
            customer_vehicle_id=booking_data.customer_vehicle_id,
            pickup_date=booking_data.pickup_date,
            notes=f"{booking_data.product_notes or ''}\n{booking_data.notes or ''}".strip(),
            status=OrderStatus.PENDING,
        )
        order_repo.add_pending(product_order)
        order_repo.flush()

        total_amount = 0.0
        order_items_info = []
        for item_data in booking_data.product_items:
            product = product_repo.get_active_product_in_shop(item_data.product_id, booking_data.shop_id)
            if not product:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {item_data.product_id} not found")
            if product.stock_quantity < item_data.quantity:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Insufficient stock for {product.name}")

            total_price = product.price * item_data.quantity
            order_repo.add_pending(
                ProductOrderItem(
                    order_id=product_order.id,
                    product_id=product.id,
                    quantity=item_data.quantity,
                    unit_price=product.price,
                    total_price=total_price,
                    product_name=product.name,
                    product_sku=product.sku,
                )
            )
            product_repo.decrease_stock(product, item_data.quantity)
            total_amount += total_price
            order_items_info.append({
                "product_id": product.id,
                "product_name": product.name,
                "quantity": item_data.quantity,
                "total_price": total_price,
            })

        product_order.total_amount = total_amount
        result["product_order"] = {
            "id": product_order.id,
            "total_amount": total_amount,
            "items": order_items_info,
            "status": product_order.status,
        }

    order_repo.commit()

    # Send notifications to shop members
    has_service = result.get("appointment") is not None
    has_product = result.get("product_order") is not None

    if has_service and has_product:
        appointment = order_repo.get_appointment(result["appointment"]["id"])
        product_order = order_repo.get_order(result["product_order"]["id"])
        customer = user_repo.get_by_id(current_user.user_id)
        customer_name = customer.full_name if customer else "Unknown"

        if appointment and product_order:
            members = shop_repo.get_active_members(booking_data.shop_id)
            total_combined = appointment.total_amount + product_order.total_amount
            for member in members:
                notification_service.create_notification(
                    user_id=member.user_id,
                    type=NotificationType.NEW_BOOKING,
                    title="🔔🔔 Combined Booking + Order",
                    message=f"{customer_name} booked SERVICE + PRODUCTS - Total: ${total_combined:.2f}",
                    appointment_id=appointment.id,
                    product_order_id=product_order.id,
                    data={
                        "customer_name": customer_name,
                        "appointment_date": appointment.appointment_date.isoformat(),
                        "vehicle_info": appointment.vehicle_info,
                        "service_total": appointment.total_amount,
                        "product_total": product_order.total_amount,
                        "combined_total": total_combined,
                        "booking_type": "combined",
                    },
                )
    elif has_service:
        appointment = order_repo.get_appointment(result["appointment"]["id"])
        if appointment:
            notification_service.notify_shop_new_booking(appointment)
    elif has_product:
        product_order = order_repo.get_order(result["product_order"]["id"])
        if product_order:
            notification_service.notify_shop_new_product_order(product_order)

    return {
        "message": "Combined booking created successfully",
        "shop_id": booking_data.shop_id,
        "customer_vehicle_id": booking_data.customer_vehicle_id,
        **result,
    }


@router.post("", response_model=ProductOrderRead, status_code=status.HTTP_201_CREATED)
def create_product_order(
    order_data: ProductOrderCreate,
    current_user: TokenData = Depends(get_current_user),
    shop_repo: ShopRepository = Depends(get_shop_repo),
    product_repo: ProductRepository = Depends(get_product_repo),
    order_repo: OrderRepository = Depends(get_order_repo),
):
    """Create a new product order (customer buying parts)."""
    # Ensure customer is associated with this shop
    user_shop = shop_repo.get_active_user_shop(current_user.user_id, order_data.shop_id)
    if not user_shop:
        shop_repo.stage_user_shop(
            UserShop(user_id=current_user.user_id, shop_id=order_data.shop_id, role="customer")
        )

    if order_data.customer_vehicle_id:
        from app.models.customer_vehicle import CustomerVehicle
        from sqlmodel import select
        vehicle = order_repo.session.exec(
            select(CustomerVehicle).where(
                CustomerVehicle.id == order_data.customer_vehicle_id,
                CustomerVehicle.customer_id == current_user.user_id,
                CustomerVehicle.is_active,
            )
        ).first()
        if not vehicle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

    order = ProductOrder(
        shop_id=order_data.shop_id,
        customer_id=current_user.user_id,
        customer_vehicle_id=order_data.customer_vehicle_id,
        pickup_date=order_data.pickup_date,
        notes=order_data.notes,
        status=OrderStatus.PENDING,
    )
    order_repo.add_pending(order)
    order_repo.flush()

    total_amount = 0.0
    for item_data in order_data.items:
        product = product_repo.get_active_product_in_shop(item_data.product_id, order_data.shop_id)
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product {item_data.product_id} not found")
        if product.stock_quantity < item_data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for {product.name}. Available: {product.stock_quantity}",
            )

        total_price = product.price * item_data.quantity
        order_repo.add_pending(
            ProductOrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=item_data.quantity,
                unit_price=product.price,
                total_price=total_price,
                product_name=product.name,
                product_sku=product.sku,
            )
        )
        product_repo.decrease_stock(product, item_data.quantity)
        total_amount += total_price

    order.total_amount = total_amount
    order_repo.commit()
    order_repo.refresh(order)

    return order


# ── Customer order views ──────────────────────────────────────────────────────

@router.get("/my-orders", response_model=List[ProductOrderRead])
def get_my_product_orders(
    order_status: Optional[OrderStatus] = None,
    current_user: TokenData = Depends(get_current_user),
    order_repo: OrderRepository = Depends(get_order_repo),
):
    """Get all product orders for logged-in customer."""
    orders = order_repo.get_orders_by_customer(current_user.user_id, order_status)
    result = []
    for order in orders:
        items = order_repo.get_order_items(order.id)
        result.append({
            "id": order.id,
            "shop_id": order.shop_id,
            "customer_id": order.customer_id,
            "customer_vehicle_id": order.customer_vehicle_id,
            "status": order.status,
            "total_amount": order.total_amount,
            "pickup_date": order.pickup_date,
            "notes": order.notes,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
            "items": items,
        })
    return result


@router.get("/my-orders/{order_id}")
def get_product_order_details(
    order_id: int,
    current_user: TokenData = Depends(get_current_user),
    order_repo: OrderRepository = Depends(get_order_repo),
):
    """Get specific product order details."""
    order = order_repo.get_order_by_customer_and_id(order_id, current_user.user_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    items = order_repo.get_order_items(order.id)
    return {
        "id": order.id,
        "shop_id": order.shop_id,
        "customer_id": order.customer_id,
        "customer_vehicle_id": order.customer_vehicle_id,
        "status": order.status,
        "total_amount": order.total_amount,
        "pickup_date": order.pickup_date,
        "notes": order.notes,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "items": items,
    }


@router.put("/my-orders/{order_id}/cancel")
def cancel_product_order(
    order_id: int,
    current_user: TokenData = Depends(get_current_user),
    order_repo: OrderRepository = Depends(get_order_repo),
    shop_repo: ShopRepository = Depends(get_shop_repo),
    user_repo: UserRepository = Depends(get_user_repo),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """Cancel a product order (only if not completed/processing)."""
    from app.models.notification import NotificationType

    order = order_repo.get_order_by_customer_and_id(order_id, current_user.user_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if order.status in [OrderStatus.COMPLETED, OrderStatus.PROCESSING]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot cancel order with status: {order.status}")

    order_repo.restore_order_stock(order_id)
    order.status = OrderStatus.CANCELLED
    order.updated_at = datetime.utcnow()
    order_repo.update_order(order)

    customer = user_repo.get_by_id(current_user.user_id)
    customer_name = customer.full_name if customer else "A customer"

    for member in shop_repo.get_active_members(order.shop_id):
        notification_service.create_notification(
            user_id=member.user_id,
            type=NotificationType.ORDER_CANCELLED,
            title="❌ Order Cancelled",
            message=f"{customer_name} cancelled their product order (Total: ${order.total_amount:.2f})",
            product_order_id=order.id,
        )

    return {"message": "Order cancelled successfully"}


# ── Pricing endpoints ─────────────────────────────────────────────────────────

@router.post("/calculate-price")
def calculate_booking_price(
    booking_data: UnifiedBookingCreate,
    current_user: TokenData = Depends(get_current_user),
    pricing_service: PricingService = Depends(get_pricing_service),
    product_repo: ProductRepository = Depends(get_product_repo),
):
    """Calculate price before booking (preview) with full transparency."""
    service_info = None
    if booking_data.service_id:
        service = product_repo.get_service(booking_data.service_id)
        if service:
            service_info = {
                "id": service.id,
                "name": service.name,
                "type": service.service_type,
                "price": service.price,
                "duration_minutes": service.duration_minutes,
                "mobile_service_fee": service.mobile_service_fee if service.service_type == "mobile" else None,
            }

    products_detail = []
    if booking_data.product_items:
        for item in booking_data.product_items:
            product = product_repo.get_product(item.product_id)
            if product:
                products_detail.append({
                    "product_id": product.id,
                    "name": product.name,
                    "sku": product.sku,
                    "image_url": product.image_url,
                    "unit_price": product.price,
                    "quantity": item.quantity,
                    "total_price": product.price * item.quantity,
                })

    price_calculation = pricing_service.calculate_appointment_price(
        service_id=booking_data.service_id,
        product_items=[item.model_dump() for item in (booking_data.product_items or [])],
        discount_amount=0.0,
    )

    return {
        "service": service_info,
        "products": products_detail,
        "pricing": {
            "service_price": price_calculation["service_price"],
            "mobile_service_fee": price_calculation["mobile_service_fee"],
            "products_subtotal": price_calculation["products_total"],
            "subtotal": price_calculation["subtotal"],
            "discount_amount": price_calculation["discount_amount"],
            "tax_amount": price_calculation["tax_amount"],
            "total_amount": price_calculation["total_amount"],
        },
    }


@router.get("/my-orders/{order_id}/price-breakdown")
def get_order_price_breakdown(
    order_id: int,
    current_user: TokenData = Depends(get_current_user),
    pricing_service: PricingService = Depends(get_pricing_service),
):
    """Get detailed price breakdown for an order."""
    breakdown = pricing_service.get_price_breakdown(order_id)
    if not breakdown:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return breakdown


# ── Shop owner order management ───────────────────────────────────────────────

@router.get("/shops/{shop_id}/orders")
def get_shop_product_orders(
    shop_id: int,
    order_status: Optional[OrderStatus] = None,
    current_user: TokenData = Depends(get_current_user),
    shop_service: ShopService = Depends(get_shop_service),
    order_repo: OrderRepository = Depends(get_order_repo),
):
    """Get all product orders for a shop (Owner/Mechanic only)."""
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only shop members can view orders")

    return order_repo.get_orders_by_shop_filtered(shop_id, order_status)


@router.put("/shops/{shop_id}/orders/{order_id}/status")
def update_product_order_status(
    shop_id: int,
    order_id: int,
    status_update: ProductOrderStatusUpdate,
    current_user: TokenData = Depends(get_current_user),
    shop_service: ShopService = Depends(get_shop_service),
    order_repo: OrderRepository = Depends(get_order_repo),
):
    """Update product order status (Owner/Mechanic only)."""
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only shop members can update orders")

    order = order_repo.get_order_by_id_and_shop(order_id, shop_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    order.status = status_update.status
    if status_update.notes:
        order.notes = f"{order.notes or ''}\n[Shop]: {status_update.notes}"
    order.updated_at = datetime.utcnow()
    order_repo.commit()
    order_repo.refresh(order)

    return order
