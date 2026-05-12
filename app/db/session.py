import os
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password123@localhost:5432/mobile_app_db"
)

# Render and some providers give postgres:// — SQLAlchemy requires postgresql://
DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
echo_sql = ENVIRONMENT == "development"

engine = create_engine(DATABASE_URL, echo=echo_sql)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
