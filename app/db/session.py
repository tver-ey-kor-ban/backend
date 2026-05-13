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

connect_args = {}
if "pgbouncer=true" in DATABASE_URL or "pooler.supabase.com" in DATABASE_URL:
    connect_args = {"prepare_threshold": None}

engine = create_engine(DATABASE_URL, echo=echo_sql, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
