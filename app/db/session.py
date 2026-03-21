from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings
import os
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.orm import sessionmaker
engine = create_engine(settings.DATABASE_URL)


def create_db_and_tables() -> None:


# Get database URL from environment or use default
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:password123@db:5432/mobile_app_db"
)

# Create engine
engine = create_engine(DATABASE_URL, echo=True)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Get database session."""
    with Session(engine) as session:
        yield session
