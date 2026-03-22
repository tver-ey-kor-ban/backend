"""Customer Vehicle endpoints for managing customer's vehicle information."""
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.db import get_session
from app.models.customer_vehicle import (
    CustomerVehicle, CustomerVehicleCreate, CustomerVehicleRead, 
    CustomerVehicleUpdate, VehicleFilterByCustomer
)
from app.core.security import get_current_user, TokenData

router = APIRouter(prefix="/my-vehicles", tags=["customer-vehicles"])


@router.post("", response_model=CustomerVehicleRead, status_code=status.HTTP_201_CREATED)
def add_vehicle(
    vehicle_data: CustomerVehicleCreate,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Add a new vehicle to customer's garage."""
    # If setting as primary, unset other primary vehicles
    if vehicle_data.is_primary:
        existing_primaries = session.exec(
            select(CustomerVehicle).where(
                CustomerVehicle.customer_id == current_user.user_id,
                CustomerVehicle.is_primary,
                CustomerVehicle.is_active
            )
        ).all()
        for v in existing_primaries:
            v.is_primary = False
    
    vehicle = CustomerVehicle(
        **vehicle_data.model_dump(),
        customer_id=current_user.user_id
    )
    session.add(vehicle)
    session.commit()
    session.refresh(vehicle)
    return vehicle


@router.get("", response_model=List[CustomerVehicleRead])
def get_my_vehicles(
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get all vehicles for logged-in customer."""
    vehicles = session.exec(
        select(CustomerVehicle).where(
            CustomerVehicle.customer_id == current_user.user_id,
            CustomerVehicle.is_active
        )
    ).all()
    return vehicles


@router.get("/primary")
def get_primary_vehicle(
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get customer's primary vehicle."""
    vehicle = session.exec(
        select(CustomerVehicle).where(
            CustomerVehicle.customer_id == current_user.user_id,
            CustomerVehicle.is_primary,
            CustomerVehicle.is_active
        )
    ).first()
    
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No primary vehicle set"
        )
    
    return vehicle


@router.get("/{vehicle_id}", response_model=CustomerVehicleRead)
def get_vehicle(
    vehicle_id: int,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get specific vehicle details."""
    vehicle = session.exec(
        select(CustomerVehicle).where(
            CustomerVehicle.id == vehicle_id,
            CustomerVehicle.customer_id == current_user.user_id,
            CustomerVehicle.is_active
        )
    ).first()
    
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    
    return vehicle


@router.put("/{vehicle_id}", response_model=CustomerVehicleRead)
def update_vehicle(
    vehicle_id: int,
    vehicle_data: CustomerVehicleUpdate,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Update vehicle information."""
    vehicle = session.exec(
        select(CustomerVehicle).where(
            CustomerVehicle.id == vehicle_id,
            CustomerVehicle.customer_id == current_user.user_id,
            CustomerVehicle.is_active
        )
    ).first()
    
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    
    # If setting as primary, unset other primary vehicles
    if vehicle_data.is_primary:
        existing_primaries = session.exec(
            select(CustomerVehicle).where(
                CustomerVehicle.customer_id == current_user.user_id,
                CustomerVehicle.is_primary,
                CustomerVehicle.is_active,
                CustomerVehicle.id != vehicle_id
            )
        ).all()
        for v in existing_primaries:
            v.is_primary = False
    
    # Update fields
    update_data = vehicle_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(vehicle, key, value)
    
    vehicle.updated_at = datetime.utcnow()
    session.commit()
    session.refresh(vehicle)
    return vehicle


@router.delete("/{vehicle_id}")
def delete_vehicle(
    vehicle_id: int,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Soft delete vehicle."""
    vehicle = session.exec(
        select(CustomerVehicle).where(
            CustomerVehicle.id == vehicle_id,
            CustomerVehicle.customer_id == current_user.user_id,
            CustomerVehicle.is_active
        )
    ).first()
    
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    
    vehicle.is_active = False
    vehicle.updated_at = datetime.utcnow()
    session.commit()
    
    return {"message": "Vehicle deleted successfully"}


@router.post("/{vehicle_id}/set-primary")
def set_primary_vehicle(
    vehicle_id: int,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Set a vehicle as primary."""
    # Unset current primary
    existing_primaries = session.exec(
        select(CustomerVehicle).where(
            CustomerVehicle.customer_id == current_user.user_id,
            CustomerVehicle.is_primary,
            CustomerVehicle.is_active
        )
    ).all()
    for v in existing_primaries:
        v.is_primary = False
    
    # Set new primary
    vehicle = session.exec(
        select(CustomerVehicle).where(
            CustomerVehicle.id == vehicle_id,
            CustomerVehicle.customer_id == current_user.user_id,
            CustomerVehicle.is_active
        )
    ).first()
    
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    
    vehicle.is_primary = True
    vehicle.updated_at = datetime.utcnow()
    session.commit()
    
    return {"message": "Primary vehicle updated", "vehicle": vehicle}


# ==================== PRODUCT FILTER BY CUSTOMER VEHICLE ====================

@router.post("/filter-products")
def filter_products_by_my_vehicle(
    filter_data: VehicleFilterByCustomer,
    shop_id: int,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Filter products compatible with customer's vehicle."""
    from app.models.product import Product
    from app.models.vehicle import ProductVehicle, VehicleEngine, VehicleYear, VehicleModel, VehicleMake
    
    # Get customer's vehicle
    vehicle = session.exec(
        select(CustomerVehicle).where(
            CustomerVehicle.id == filter_data.customer_vehicle_id,
            CustomerVehicle.customer_id == current_user.user_id,
            CustomerVehicle.is_active
        )
    ).first()
    
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    
    # Find matching vehicle in database
    # Match by make, model, year (and optionally engine)
    query = select(VehicleEngine).join(VehicleYear).join(VehicleModel).join(VehicleMake).where(
        VehicleMake.name.ilike(vehicle.make),
        VehicleModel.name.ilike(vehicle.model),
        VehicleYear.year == vehicle.year,
        VehicleEngine.is_active
    )
    
    if vehicle.engine:
        query = query.where(VehicleEngine.engine_code.ilike(f"%{vehicle.engine}%"))
    
    if vehicle.fuel_type:
        query = query.where(VehicleEngine.fuel_type == vehicle.fuel_type)
    
    matching_engines = session.exec(query).all()
    
    if not matching_engines:
        return {
            "message": "No matching vehicle found in database",
            "vehicle": vehicle,
            "products": []
        }
    
    engine_ids = [e.id for e in matching_engines]
    
    # Get products compatible with these engines
    product_query = select(Product).join(ProductVehicle).where(
        Product.shop_id == shop_id,
        Product.is_active,
        ProductVehicle.vehicle_engine_id.in_(engine_ids)
    )
    
    if filter_data.category_id:
        product_query = product_query.where(Product.category_id == filter_data.category_id)
    
    products = session.exec(product_query).all()
    
    return {
        "vehicle": vehicle,
        "matching_engines": len(engine_ids),
        "products": products
    }
