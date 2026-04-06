"""Product Order endpoints for customer self-service purchases."""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, SQLModel

from app.db import get_session
from app.models.product_order import (
    ProductOrder, ProductOrderItem, ProductOrderCreate, ProductOrderRead,
    ProductOrderStatusUpdate, OrderStatus, ProductOrderItemCreate
)
from app.models.shop import UserShop
from app.core.security import get_current_user, TokenData

router = APIRouter(prefix="/product-orders", tags=["product-orders"])


# ==================== UNIFIED BOOKING (Service + Products) ====================

class UnifiedBookingCreate(SQLModel):
    """Unified booking - can be service only, products only, or both."""
    shop_id: int
    customer_vehicle_id: Optional[int] = None
    vehicle_info: Optional[str] = None
    
    # Vehicle details (for auto-saving if customer_vehicle_id not provided)
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_year: Optional[int] = None
    vehicle_engine: Optional[str] = None
    vehicle_fuel_type: Optional[str] = None
    vehicle_license_plate: Optional[str] = None
    
    # Service info (optional - for service appointments)
    service_id: Optional[int] = None
    service_notes: Optional[str] = None
    appointment_date: Optional[datetime] = None
    
    # Product info (optional - for product orders)
    product_items: Optional[List[ProductOrderItemCreate]] = []
    product_notes: Optional[str] = None
    
    # Pickup/Delivery info
    pickup_date: Optional[datetime] = None
    
    # Mobile service - customer location
    customer_address: Optional[str] = None  # For mobile services
    customer_phone: Optional[str] = None    # For contact
    customer_location_lat: Optional[float] = None  # GPS coordinates
    customer_location_lng: Optional[float] = None
    
    # Combined notes
    notes: Optional[str] = None


@router.post("/unified-booking", status_code=status.HTTP_201_CREATED)
def create_unified_booking(
    booking_data: UnifiedBookingCreate,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Book service AND order products at the same time."""
    from app.models.appointment import Appointment, AppointmentStatus
    from app.models.product import Product
    from app.models.customer_vehicle import CustomerVehicle
    
    result = {
        "appointment": None,
        "product_order": None
    }
    
    # Verify customer is associated with this shop
    user_shop = session.exec(
        select(UserShop).where(
            UserShop.user_id == current_user.user_id,
            UserShop.shop_id == booking_data.shop_id,
            UserShop.is_active
        )
    ).first()
    
    if not user_shop:
        user_shop = UserShop(
            user_id=current_user.user_id,
            shop_id=booking_data.shop_id,
            role="customer"
        )
        session.add(user_shop)
        session.flush()
    
    # Handle vehicle - validate existing or auto-save new
    customer_vehicle_id = booking_data.customer_vehicle_id
    
    if customer_vehicle_id:
        # Validate existing vehicle
        vehicle = session.exec(
            select(CustomerVehicle).where(
                CustomerVehicle.id == customer_vehicle_id,
                CustomerVehicle.customer_id == current_user.user_id,
                CustomerVehicle.is_active
            )
        ).first()
        if not vehicle:
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
    
    # Calculate pricing
    from app.services.pricing_service import PricingService
    pricing_service = PricingService(session)
    
    price_calculation = pricing_service.calculate_appointment_price(
        service_id=booking_data.service_id,
        product_items=[item.model_dump() for item in (booking_data.product_items or [])],
        discount_amount=0.0
    )
    
    # 1. Create Service Appointment (if service_id provided)
    if booking_data.service_id:
        # Get service details to check if mobile
        from app.models.product import Service, ServiceType
        service = session.get(Service, booking_data.service_id)
        
        # Build notes with location info for mobile services
        appointment_notes = booking_data.service_notes or ""
        if booking_data.notes:
            appointment_notes += f"\n{booking_data.notes}"
        
        # Add location info for mobile services
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
            total_amount=price_calculation["total_amount"]
        )
        session.add(appointment)
        session.flush()
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
                "total": appointment.total_amount
            }
        }
    
    # 2. Create Product Order (if products provided)
    if booking_data.product_items:
        product_order = ProductOrder(
            shop_id=booking_data.shop_id,
            customer_id=current_user.user_id,
            customer_vehicle_id=booking_data.customer_vehicle_id,
            pickup_date=booking_data.pickup_date,
            notes=f"{booking_data.product_notes or ''}\n{booking_data.notes or ''}".strip(),
            status=OrderStatus.PENDING
        )
        session.add(product_order)
        session.flush()
        
        # Add order items
        total_amount = 0.0
        order_items = []
        for item_data in booking_data.product_items:
            product = session.exec(
                select(Product).where(
                    Product.id == item_data.product_id,
                    Product.shop_id == booking_data.shop_id,
                    Product.is_active
                )
            ).first()
            
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product {item_data.product_id} not found"
                )
            
            if product.stock_quantity < item_data.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock for {product.name}"
                )
            
            unit_price = product.price
            total_price = unit_price * item_data.quantity
            
            order_item = ProductOrderItem(
                order_id=product_order.id,
                product_id=product.id,
                quantity=item_data.quantity,
                unit_price=unit_price,
                total_price=total_price,
                product_name=product.name,
                product_sku=product.sku
            )
            session.add(order_item)
            product.stock_quantity -= item_data.quantity
            total_amount += total_price
            order_items.append({
                "product_id": product.id,
                "product_name": product.name,
                "quantity": item_data.quantity,
                "total_price": total_price
            })
        
        product_order.total_amount = total_amount
        result["product_order"] = {
            "id": product_order.id,
            "total_amount": total_amount,
            "items": order_items,
            "status": product_order.status
        }
    
    session.commit()
    
    # Send notifications to shop members
    from app.services.notification_service import NotificationService
    from app.models.notification import NotificationType
    
    notification_service = NotificationService(session)
    
    # Get customer info
    from app.models.user import User
    customer = session.get(User, current_user.user_id)
    customer_name = customer.full_name if customer else "Unknown"
    
    # Check if this is a combined booking (both service + product)
    has_service = result.get("appointment") is not None
    has_product = result.get("product_order") is not None
    
    if has_service and has_product:
        # Combined booking - send unified notification
        appointment = session.get(Appointment, result["appointment"]["id"])
        product_order = session.get(ProductOrder, result["product_order"]["id"])
        
        if appointment and product_order:
            # Get shop members
            members = session.exec(
                select(UserShop).where(
                    UserShop.shop_id == booking_data.shop_id,
                    UserShop.is_active
                )
            ).all()
            
            total_amount = appointment.total_amount + product_order.total_amount
            
            for member in members:
                notification_service.create_notification(
                    user_id=member.user_id,
                    type=NotificationType.NEW_BOOKING,
                    title="🔔🔔 Combined Booking + Order",
                    message=f"{customer_name} booked SERVICE + PRODUCTS - Total: ${total_amount:.2f}",
                    appointment_id=appointment.id,
                    product_order_id=product_order.id,
                    data={
                        "customer_name": customer_name,
                        "appointment_date": appointment.appointment_date.isoformat(),
                        "vehicle_info": appointment.vehicle_info,
                        "service_total": appointment.total_amount,
                        "product_total": product_order.total_amount,
                        "combined_total": total_amount,
                        "booking_type": "combined"
                    }
                )
    
    elif has_service:
        # Service only
        appointment = session.get(Appointment, result["appointment"]["id"])
        if appointment:
            notification_service.notify_shop_new_booking(appointment)
    
    elif has_product:
        # Product only
        product_order = session.get(ProductOrder, result["product_order"]["id"])
        if product_order:
            notification_service.notify_shop_new_product_order(product_order)
    
    return {
        "message": "Combined booking created successfully",
        "shop_id": booking_data.shop_id,
        "customer_vehicle_id": booking_data.customer_vehicle_id,
        **result
    }


@router.post("", response_model=ProductOrderRead, status_code=status.HTTP_201_CREATED)
def create_product_order(
    order_data: ProductOrderCreate,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Create a new product order (customer buying parts)."""
    from app.models.product import Product
    
    # Verify customer is associated with this shop
    user_shop = session.exec(
        select(UserShop).where(
            UserShop.user_id == current_user.user_id,
            UserShop.shop_id == order_data.shop_id,
            UserShop.is_active
        )
    ).first()
    
    # If not associated, create customer relationship
    if not user_shop:
        user_shop = UserShop(
            user_id=current_user.user_id,
            shop_id=order_data.shop_id,
            role="customer"
        )
        session.add(user_shop)
        session.flush()
    
    # Validate customer vehicle if provided
    if order_data.customer_vehicle_id:
        from app.models.customer_vehicle import CustomerVehicle
        vehicle = session.exec(
            select(CustomerVehicle).where(
                CustomerVehicle.id == order_data.customer_vehicle_id,
                CustomerVehicle.customer_id == current_user.user_id,
                CustomerVehicle.is_active
            )
        ).first()
        if not vehicle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehicle not found"
            )
    
    # Create order
    order = ProductOrder(
        shop_id=order_data.shop_id,
        customer_id=current_user.user_id,
        customer_vehicle_id=order_data.customer_vehicle_id,
        pickup_date=order_data.pickup_date,
        notes=order_data.notes,
        status=OrderStatus.PENDING
    )
    session.add(order)
    session.flush()  # Get order ID
    
    # Add order items
    total_amount = 0.0
    for item_data in order_data.items:
        # Get product
        product = session.exec(
            select(Product).where(
                Product.id == item_data.product_id,
                Product.shop_id == order_data.shop_id,
                Product.is_active
            )
        ).first()
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {item_data.product_id} not found"
            )
        
        # Check stock
        if product.stock_quantity < item_data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for {product.name}. Available: {product.stock_quantity}"
            )
        
        # Calculate prices
        unit_price = product.price
        total_price = unit_price * item_data.quantity
        
        # Create order item
        order_item = ProductOrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=item_data.quantity,
            unit_price=unit_price,
            total_price=total_price,
            product_name=product.name,
            product_sku=product.sku
        )
        session.add(order_item)
        
        # Update product stock (reserve items)
        product.stock_quantity -= item_data.quantity
        
        total_amount += total_price
    
    order.total_amount = total_amount
    session.commit()
    session.refresh(order)
    
    return order


@router.get("/my-orders", response_model=List[ProductOrderRead])
def get_my_product_orders(
    status: Optional[OrderStatus] = None,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get all product orders for logged-in customer."""
    query = select(ProductOrder).where(
        ProductOrder.customer_id == current_user.user_id
    )
    
    if status:
        query = query.where(ProductOrder.status == status)
    
    query = query.order_by(ProductOrder.created_at.desc())
    orders = session.exec(query).all()
    
    # Load items for each order
    result = []
    for order in orders:
        items = session.exec(
            select(ProductOrderItem).where(ProductOrderItem.order_id == order.id)
        ).all()
        order_dict = {
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
            "items": items
        }
        result.append(order_dict)
    
    return result


@router.get("/my-orders/{order_id}")
def get_product_order_details(
    order_id: int,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get specific product order details."""
    order = session.exec(
        select(ProductOrder).where(
            ProductOrder.id == order_id,
            ProductOrder.customer_id == current_user.user_id
        )
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    items = session.exec(
        select(ProductOrderItem).where(ProductOrderItem.order_id == order.id)
    ).all()
    
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
        "items": items
    }


@router.put("/my-orders/{order_id}/cancel")
def cancel_product_order(
    order_id: int,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Cancel a product order (only if not completed/processing)."""
    from app.models.product import Product
    
    order = session.exec(
        select(ProductOrder).where(
            ProductOrder.id == order_id,
            ProductOrder.customer_id == current_user.user_id
        )
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    if order.status in [OrderStatus.COMPLETED, OrderStatus.PROCESSING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel order with status: {order.status}"
        )
    
    # Restore stock
    items = session.exec(
        select(ProductOrderItem).where(ProductOrderItem.order_id == order.id)
    ).all()
    
    for item in items:
        product = session.get(Product, item.product_id)
        if product:
            product.stock_quantity += item.quantity
    
    order.status = OrderStatus.CANCELLED
    order.updated_at = datetime.utcnow()
    session.commit()
    
    # Notify shop members about cancellation
    from app.services.notification_service import NotificationService
    from app.models.shop import UserShop
    from app.models.notification import NotificationType
    from app.models.user import User
    
    notification_service = NotificationService(session)
    
    # Get customer info
    customer = session.get(User, current_user.user_id)
    customer_name = customer.full_name if customer else "A customer"
    
    # Notify shop members
    members = session.exec(
        select(UserShop).where(
            UserShop.shop_id == order.shop_id,
            UserShop.is_active
        )
    ).all()
    
    for member in members:
        notification_service.create_notification(
            user_id=member.user_id,
            type=NotificationType.ORDER_CANCELLED,
            title="❌ Order Cancelled",
            message=f"{customer_name} cancelled their product order (Total: ${order.total_amount:.2f})",
            product_order_id=order.id
        )
    
    return {"message": "Order cancelled successfully"}


# ==================== PRICING ENDPOINTS ====================

@router.post("/calculate-price")
def calculate_booking_price(
    booking_data: UnifiedBookingCreate,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Calculate price before booking (preview) with full transparency."""
    from app.services.pricing_service import PricingService
    from app.models.product import Product, Service
    
    pricing_service = PricingService(session)
    
    # Get service details
    service_info = None
    if booking_data.service_id:
        service = session.get(Service, booking_data.service_id)
        if service:
            service_info = {
                "id": service.id,
                "name": service.name,
                "type": service.service_type,
                "price": service.price,
                "duration_minutes": service.duration_minutes,
                "mobile_service_fee": service.mobile_service_fee if service.service_type == "mobile" else None
            }
    
    # Get product details with individual prices
    products_detail = []
    if booking_data.product_items:
        for item in booking_data.product_items:
            product = session.get(Product, item.product_id)
            if product:
                products_detail.append({
                    "product_id": product.id,
                    "name": product.name,
                    "sku": product.sku,
                    "image_url": product.image_url,
                    "unit_price": product.price,
                    "quantity": item.quantity,
                    "total_price": product.price * item.quantity
                })
    
    # Calculate pricing
    price_calculation = pricing_service.calculate_appointment_price(
        service_id=booking_data.service_id,
        product_items=[item.model_dump() for item in (booking_data.product_items or [])],
        discount_amount=0.0
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
            "total_amount": price_calculation["total_amount"]
        }
    }


@router.get("/my-orders/{order_id}/price-breakdown")
def get_order_price_breakdown(
    order_id: int,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get detailed price breakdown for an order."""
    from app.services.pricing_service import PricingService
    
    pricing_service = PricingService(session)
    breakdown = pricing_service.get_price_breakdown(order_id)
    
    if not breakdown:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    return breakdown


# ==================== SHOP OWNER ORDER MANAGEMENT ====================

@router.get("/shops/{shop_id}/orders")
def get_shop_product_orders(
    shop_id: int,
    status: Optional[OrderStatus] = None,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get all product orders for a shop (Owner/Mechanic only)."""
    from app.services.shop_service import ShopService
    
    shop_service = ShopService(session)
    
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop members can view orders"
        )
    
    query = select(ProductOrder).where(ProductOrder.shop_id == shop_id)
    
    if status:
        query = query.where(ProductOrder.status == status)
    
    query = query.order_by(ProductOrder.created_at.desc())
    orders = session.exec(query).all()
    
    return orders


@router.put("/shops/{shop_id}/orders/{order_id}/status")
def update_product_order_status(
    shop_id: int,
    order_id: int,
    status_update: ProductOrderStatusUpdate,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Update product order status (Owner/Mechanic only)."""
    from app.services.shop_service import ShopService
    
    shop_service = ShopService(session)
    
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop members can update orders"
        )
    
    order = session.exec(
        select(ProductOrder).where(
            ProductOrder.id == order_id,
            ProductOrder.shop_id == shop_id
        )
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    order.status = status_update.status
    if status_update.notes:
        order.notes = f"{order.notes or ''}\n[Shop]: {status_update.notes}"
    order.updated_at = datetime.utcnow()
    
    session.commit()
    session.refresh(order)
    
    return order
