"""Service endpoints - Shop Owner only for write operations."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select

from app.db import get_session
from app.models.product import Service, ServiceCreate, ServiceRead, ServiceType
from app.core.security import TokenData
from app.core.dependencies import require_shop_owner, require_shop_member

router = APIRouter(tags=["services"])


@router.post("/shops/{shop_id}/services", response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
def create_service(
    shop_id: int,
    service_data: ServiceCreate,
    current_user: TokenData = Depends(require_shop_owner),
    session: Session = Depends(get_session)
):
    """Create a new service in shop. Only shop owner can create."""
    service = Service(
        **service_data.model_dump(),
        shop_id=shop_id
    )
    session.add(service)
    session.commit()
    session.refresh(service)
    return service


@router.get("/shops/{shop_id}/services", response_model=List[ServiceRead])
def list_services(
    shop_id: int,
    service_type: Optional[ServiceType] = Query(None, description="Filter by service type: shop_based, mobile, pickup_drop"),
    current_user: TokenData = Depends(require_shop_member),
    session: Session = Depends(get_session)
):
    """List all services in shop. Shop members (owner/mechanic) can view.
    
    Optional filter by service_type:
    - shop_based: Customer brings vehicle to shop
    - mobile: Mechanic goes to customer location  
    - pickup_drop: Shop picks up vehicle, services, returns
    """
    statement = select(Service).where(
        Service.shop_id == shop_id,
        Service.is_active
    )
    
    if service_type:
        statement = statement.where(Service.service_type == service_type)
    
    services = session.exec(statement).all()
    return services


@router.get("/shops/{shop_id}/services/by-type")
def list_services_by_type(
    shop_id: int,
    current_user: TokenData = Depends(require_shop_member),
    session: Session = Depends(get_session)
):
    """Get services grouped by type for easy viewing."""
    # Get all active services for the shop
    services = session.exec(
        select(Service).where(
            Service.shop_id == shop_id,
            Service.is_active
        )
    ).all()
    
    # Group by service type
    result = {
        "shop_based": [],
        "mobile": [],
        "pickup_drop": []
    }
    
    for service in services:
        service_data = {
            "id": service.id,
            "name": service.name,
            "description": service.description,
            "price": service.price,
            "duration_minutes": service.duration_minutes,
            "image_url": service.image_url
        }
        
        if service.service_type == ServiceType.MOBILE:
            service_data["mobile_service_area"] = service.mobile_service_area
            service_data["mobile_service_fee"] = service.mobile_service_fee
            result["mobile"].append(service_data)
        elif service.service_type == ServiceType.PICKUP_DROP:
            result["pickup_drop"].append(service_data)
        else:
            result["shop_based"].append(service_data)
    
    # Add counts
    result["counts"] = {
        "shop_based": len(result["shop_based"]),
        "mobile": len(result["mobile"]),
        "pickup_drop": len(result["pickup_drop"]),
        "total": len(services)
    }
    
    return result


@router.get("/shops/{shop_id}/services/{service_id}", response_model=ServiceRead)
def get_service(
    shop_id: int,
    service_id: int,
    current_user: TokenData = Depends(require_shop_member),
    session: Session = Depends(get_session)
):
    """Get service details. Shop members can view."""
    statement = select(Service).where(
        Service.id == service_id,
        Service.shop_id == shop_id,
        Service.is_active
    )
    service = session.exec(statement).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    return service


@router.put("/shops/{shop_id}/services/{service_id}", response_model=ServiceRead)
def update_service(
    shop_id: int,
    service_id: int,
    service_data: ServiceCreate,
    current_user: TokenData = Depends(require_shop_owner),
    session: Session = Depends(get_session)
):
    """Update service. Only shop owner can update."""
    statement = select(Service).where(
        Service.id == service_id,
        Service.shop_id == shop_id,
        Service.is_active
    )
    service = session.exec(statement).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    # Update fields
    for key, value in service_data.model_dump().items():
        setattr(service, key, value)
    
    session.commit()
    session.refresh(service)
    return service


@router.delete("/shops/{shop_id}/services/{service_id}")
def delete_service(
    shop_id: int,
    service_id: int,
    current_user: TokenData = Depends(require_shop_owner),
    session: Session = Depends(get_session)
):
    """Delete service (soft delete). Only shop owner can delete."""
    statement = select(Service).where(
        Service.id == service_id,
        Service.shop_id == shop_id,
        Service.is_active
    )
    service = session.exec(statement).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    service.is_active = False
    session.commit()
    return {"message": "Service deleted successfully"}
