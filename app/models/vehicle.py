"""Vehicle models for garage service - Make, Model, Year, Engine, etc."""
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from app.models.product import Product


class VehicleMake(SQLModel, table=True):
    """Vehicle manufacturers (Toyota, Honda, Ford, etc.)"""
    __tablename__ = "vehicle_makes"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)  # Toyota, Honda, BMW
    country: Optional[str] = None
    is_active: bool = True
    
    # Relationships
    models: List["VehicleModel"] = Relationship(back_populates="make")


class VehicleModel(SQLModel, table=True):
    """Vehicle models (Camry, Civic, F-150, etc.)"""
    __tablename__ = "vehicle_models"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    make_id: int = Field(foreign_key="vehicle_makes.id", index=True)
    name: str = Field(index=True)  # Camry, Civic, X5
    vehicle_type: Optional[str] = None  # Sedan, SUV, Truck, Motorcycle
    is_active: bool = True
    
    # Relationships
    make: VehicleMake = Relationship(back_populates="models")
    years: List["VehicleYear"] = Relationship(back_populates="model")


class VehicleYear(SQLModel, table=True):
    """Vehicle model years with engine options"""
    __tablename__ = "vehicle_years"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    model_id: int = Field(foreign_key="vehicle_models.id", index=True)
    year: int = Field(index=True)  # 2020, 2021, 2022
    is_active: bool = True
    
    # Relationships
    model: VehicleModel = Relationship(back_populates="years")
    engines: List["VehicleEngine"] = Relationship(back_populates="year")


class VehicleEngine(SQLModel, table=True):
    """Engine specifications for specific year/model"""
    __tablename__ = "vehicle_engines"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    year_id: int = Field(foreign_key="vehicle_years.id", index=True)
    engine_code: Optional[str] = None  # 2GR-FE, K20C1
    displacement: Optional[str] = None  # 2.5L, 3.0L
    cylinders: Optional[int] = None  # 4, 6, 8
    fuel_type: str = Field(default="gasoline")  # gasoline, diesel, hybrid, electric
    power_hp: Optional[int] = None  # Horsepower
    torque_nm: Optional[int] = None  # Torque
    is_active: bool = True
    
    # Relationships
    year: VehicleYear = Relationship(back_populates="engines")
    products: List["ProductVehicle"] = Relationship(back_populates="vehicle_engine")


class ProductVehicle(SQLModel, table=True):
    """Many-to-many: Products compatible with specific vehicles"""
    __tablename__ = "product_vehicles"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="products.id")
    vehicle_engine_id: int = Field(foreign_key="vehicle_engines.id")
    notes: Optional[str] = None  # "Fits with modification", "OEM Part"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    vehicle_engine: VehicleEngine = Relationship(back_populates="products")
    product: "Product" = Relationship(back_populates="vehicle_compatibilities")


# Pydantic models for API
class VehicleMakeRead(SQLModel):
    id: int
    name: str
    country: Optional[str]


class VehicleModelRead(SQLModel):
    id: int
    make_id: int
    name: str
    vehicle_type: Optional[str]


class VehicleYearRead(SQLModel):
    id: int
    model_id: int
    year: int


class VehicleEngineRead(SQLModel):
    id: int
    year_id: int
    engine_code: Optional[str]
    displacement: Optional[str]
    cylinders: Optional[int]
    fuel_type: str
    power_hp: Optional[int]
    torque_nm: Optional[int]


class VehicleFilterRequest(SQLModel):
    """Request model for filtering products by vehicle"""
    make_id: Optional[int] = None
    model_id: Optional[int] = None
    year: Optional[int] = None
    engine_id: Optional[int] = None
    fuel_type: Optional[str] = None


class VehicleFullInfo(SQLModel):
    """Full vehicle information for display"""
    make: str
    model: str
    year: int
    engine: Optional[str]
    fuel_type: str
    displacement: Optional[str]
