"""Vehicle endpoints for filtering products by vehicle specs."""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.db import get_session
from app.models.vehicle import (
    VehicleMake, VehicleModel, VehicleYear, VehicleEngine,
    VehicleMakeRead, VehicleModelRead, VehicleYearRead, VehicleEngineRead
)

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("/makes", response_model=List[VehicleMakeRead])
def list_makes(
    session: Session = Depends(get_session)
):
    """Get all vehicle makes (brands)."""
    statement = select(VehicleMake).where(VehicleMake.is_active)
    return session.exec(statement).all()


@router.get("/makes/{make_id}/models", response_model=List[VehicleModelRead])
def list_models_by_make(
    make_id: int,
    session: Session = Depends(get_session)
):
    """Get all models for a specific make."""
    statement = select(VehicleModel).where(
        VehicleModel.make_id == make_id,
        VehicleModel.is_active
    )
    return session.exec(statement).all()


@router.get("/models/{model_id}/years", response_model=List[VehicleYearRead])
def list_years_by_model(
    model_id: int,
    session: Session = Depends(get_session)
):
    """Get all years for a specific model."""
    statement = select(VehicleYear).where(
        VehicleYear.model_id == model_id,
        VehicleYear.is_active
    )
    return session.exec(statement).all()


@router.get("/years/{year_id}/engines", response_model=List[VehicleEngineRead])
def list_engines_by_year(
    year_id: int,
    session: Session = Depends(get_session)
):
    """Get all engine options for a specific year."""
    statement = select(VehicleEngine).where(
        VehicleEngine.year_id == year_id,
        VehicleEngine.is_active
    )
    return session.exec(statement).all()


@router.get("/search")
def search_vehicle(
    make: Optional[str] = Query(None, description="Vehicle make (Toyota, Honda)"),
    model: Optional[str] = Query(None, description="Vehicle model (Camry, Civic)"),
    year: Optional[int] = Query(None, description="Vehicle year (2020, 2021)"),
    session: Session = Depends(get_session)
):
    """Search for vehicle by make, model, year."""
    results = []
    
    query = select(VehicleMake, VehicleModel, VehicleYear, VehicleEngine).join(
        VehicleModel, VehicleModel.make_id == VehicleMake.id
    ).join(
        VehicleYear, VehicleYear.model_id == VehicleModel.id
    ).join(
        VehicleEngine, VehicleEngine.year_id == VehicleYear.id
    ).where(
        VehicleMake.is_active,
        VehicleModel.is_active,
        VehicleYear.is_active,
        VehicleEngine.is_active
    )
    
    if make:
        query = query.where(VehicleMake.name.ilike(f"%{make}%"))
    if model:
        query = query.where(VehicleModel.name.ilike(f"%{model}%"))
    if year:
        query = query.where(VehicleYear.year == year)
    
    rows = session.exec(query).all()
    
    for make_obj, model_obj, year_obj, engine_obj in rows:
        results.append({
            "engine_id": engine_obj.id,
            "make": make_obj.name,
            "model": model_obj.name,
            "year": year_obj.year,
            "engine_code": engine_obj.engine_code,
            "displacement": engine_obj.displacement,
            "fuel_type": engine_obj.fuel_type,
            "cylinders": engine_obj.cylinders
        })
    
    return results


@router.get("/fuel-types")
def list_fuel_types():
    """Get all available fuel types."""
    return ["gasoline", "diesel", "hybrid", "electric", "plugin_hybrid"]


@router.get("/validate")
def validate_vehicle_combination(
    make_id: int,
    model_id: int,
    year_id: int,
    engine_id: int,
    session: Session = Depends(get_session)
):
    """Validate that the vehicle combination is correct (make->model->year->engine)."""
    # Get engine with all parent relationships
    engine = session.get(VehicleEngine, engine_id)
    if not engine:
        return {"valid": False, "error": "Engine not found"}
    
    year = session.get(VehicleYear, engine.year_id)
    if not year or year.id != year_id:
        return {"valid": False, "error": "Year does not match engine"}
    
    model = session.get(VehicleModel, year.model_id)
    if not model or model.id != model_id:
        return {"valid": False, "error": "Model does not match year"}
    
    make = session.get(VehicleMake, model.make_id)
    if not make or make.id != make_id:
        return {"valid": False, "error": "Make does not match model"}
    
    return {
        "valid": True,
        "vehicle": {
            "make": make.name,
            "model": model.name,
            "year": year.year,
            "engine": engine.engine_code,
            "fuel_type": engine.fuel_type
        }
    }


@router.get("/hierarchy")
def get_vehicle_hierarchy(
    make_id: Optional[int] = None,
    model_id: Optional[int] = None,
    year_id: Optional[int] = None,
    session: Session = Depends(get_session)
):
    """Get the full hierarchy from make down to engine based on provided IDs."""
    result = {}
    
    if make_id:
        make = session.get(VehicleMake, make_id)
        if make:
            result["make"] = {"id": make.id, "name": make.name}
            
            # Get models for this make
            models = session.exec(
                select(VehicleModel).where(
                    VehicleModel.make_id == make_id,
                    VehicleModel.is_active
                )
            ).all()
            result["models"] = [{"id": m.id, "name": m.name} for m in models]
    
    if model_id:
        model = session.get(VehicleModel, model_id)
        if model:
            result["model"] = {"id": model.id, "name": model.name}
            
            # Verify model belongs to selected make
            if make_id and model.make_id != make_id:
                result["error"] = "Model does not belong to selected make"
                return result
            
            # Get years for this model
            years = session.exec(
                select(VehicleYear).where(
                    VehicleYear.model_id == model_id,
                    VehicleYear.is_active
                )
            ).all()
            result["years"] = [{"id": y.id, "year": y.year} for y in years]
    
    if year_id:
        year = session.get(VehicleYear, year_id)
        if year:
            result["year"] = {"id": year.id, "year": year.year}
            
            # Verify year belongs to selected model
            if model_id and year.model_id != model_id:
                result["error"] = "Year does not belong to selected model"
                return result
            
            # Get engines for this year
            engines = session.exec(
                select(VehicleEngine).where(
                    VehicleEngine.year_id == year_id,
                    VehicleEngine.is_active
                )
            ).all()
            result["engines"] = [{"id": e.id, "code": e.engine_code, "fuel": e.fuel_type} for e in engines]
    
    return result
