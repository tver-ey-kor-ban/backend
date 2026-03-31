"""Seed vehicle database with common makes and models."""
from sqlmodel import Session, select

from app.models.vehicle import VehicleMake, VehicleModel, VehicleYear, VehicleEngine


def seed_vehicles(session: Session):
    """Seed database with common vehicle data."""
    
    # Check if already seeded
    existing = session.exec(select(VehicleMake)).first()
    if existing:
        print("Vehicle data already seeded")
        return
    
    # Toyota
    toyota = VehicleMake(name="Toyota", country="Japan")
    session.add(toyota)
    session.flush()
    
    # Toyota Camry
    camry = VehicleModel(make_id=toyota.id, name="Camry", vehicle_type="Sedan")
    session.add(camry)
    session.flush()
    
    # Camry 2020-2024
    for year in range(2020, 2025):
        camry_year = VehicleYear(model_id=camry.id, year=year)
        session.add(camry_year)
        session.flush()
        
        # Engine options
        engines = [
            {"code": "2.5L 4-Cyl", "displacement": "2.5L", "cylinders": 4, "fuel": "gasoline", "hp": 203},
            {"code": "3.5L V6", "displacement": "3.5L", "cylinders": 6, "fuel": "gasoline", "hp": 301},
        ]
        if year >= 2021:
            engines.append({"code": "Hybrid 2.5L", "displacement": "2.5L", "cylinders": 4, "fuel": "hybrid", "hp": 208})
        
        for eng in engines:
            engine = VehicleEngine(
                year_id=camry_year.id,
                engine_code=eng["code"],
                displacement=eng["displacement"],
                cylinders=eng["cylinders"],
                fuel_type=eng["fuel"],
                power_hp=eng["hp"]
            )
            session.add(engine)
    
    # Toyota Corolla
    corolla = VehicleModel(make_id=toyota.id, name="Corolla", vehicle_type="Sedan")
    session.add(corolla)
    session.flush()
    
    for year in range(2020, 2025):
        corolla_year = VehicleYear(model_id=corolla.id, year=year)
        session.add(corolla_year)
        session.flush()
        
        engines = [
            {"code": "1.8L 4-Cyl", "displacement": "1.8L", "cylinders": 4, "fuel": "gasoline", "hp": 139},
            {"code": "2.0L 4-Cyl", "displacement": "2.0L", "cylinders": 4, "fuel": "gasoline", "hp": 169},
        ]
        if year >= 2020:
            engines.append({"code": "Hybrid 1.8L", "displacement": "1.8L", "cylinders": 4, "fuel": "hybrid", "hp": 121})
        
        for eng in engines:
            engine = VehicleEngine(
                year_id=corolla_year.id,
                engine_code=eng["code"],
                displacement=eng["displacement"],
                cylinders=eng["cylinders"],
                fuel_type=eng["fuel"],
                power_hp=eng["hp"]
            )
            session.add(engine)
    
    # Honda
    honda = VehicleMake(name="Honda", country="Japan")
    session.add(honda)
    session.flush()
    
    # Honda Civic
    civic = VehicleModel(make_id=honda.id, name="Civic", vehicle_type="Sedan")
    session.add(civic)
    session.flush()
    
    for year in range(2020, 2025):
        civic_year = VehicleYear(model_id=civic.id, year=year)
        session.add(civic_year)
        session.flush()
        
        engines = [
            {"code": "2.0L 4-Cyl", "displacement": "2.0L", "cylinders": 4, "fuel": "gasoline", "hp": 158},
            {"code": "1.5L Turbo", "displacement": "1.5L", "cylinders": 4, "fuel": "gasoline", "hp": 180},
        ]
        
        for eng in engines:
            engine = VehicleEngine(
                year_id=civic_year.id,
                engine_code=eng["code"],
                displacement=eng["displacement"],
                cylinders=eng["cylinders"],
                fuel_type=eng["fuel"],
                power_hp=eng["hp"]
            )
            session.add(engine)
    
    # Ford
    ford = VehicleMake(name="Ford", country="USA")
    session.add(ford)
    session.flush()
    
    # Ford F-150
    f150 = VehicleModel(make_id=ford.id, name="F-150", vehicle_type="Truck")
    session.add(f150)
    session.flush()
    
    for year in range(2020, 2025):
        f150_year = VehicleYear(model_id=f150.id, year=year)
        session.add(f150_year)
        session.flush()
        
        engines = [
            {"code": "3.3L V6", "displacement": "3.3L", "cylinders": 6, "fuel": "gasoline", "hp": 290},
            {"code": "2.7L EcoBoost", "displacement": "2.7L", "cylinders": 6, "fuel": "gasoline", "hp": 325},
            {"code": "5.0L V8", "displacement": "5.0L", "cylinders": 8, "fuel": "gasoline", "hp": 400},
        ]
        
        for eng in engines:
            engine = VehicleEngine(
                year_id=f150_year.id,
                engine_code=eng["code"],
                displacement=eng["displacement"],
                cylinders=eng["cylinders"],
                fuel_type=eng["fuel"],
                power_hp=eng["hp"]
            )
            session.add(engine)
    
    session.commit()
    print("Vehicle database seeded successfully!")
