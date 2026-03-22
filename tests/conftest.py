import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set a minimal Firebase credential for testing (won't be used with mocks)
os.environ["FIREBASE_CREDENTIALS_PATH"] = ""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from app.main import app
from app.db import get_session
from app.models.user import User
from app.core.security import create_access_token, get_password_hash


# Create in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(name="engine")
def engine_fixture():
    """Create a test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="session")
def session_fixture(engine):
    """Create a test database session."""
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session):
    """Create a test client with overridden dependencies."""
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="test_user")
def test_user_fixture(session):
    """Create a test user with proper password."""
    user = User(
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        hashed_password=get_password_hash("testpassword"),
        roles="user",
        is_active=True,
        is_superuser=False
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="admin_user")
def admin_user_fixture(session):
    """Create an admin test user with proper password."""
    user = User(
        email="admin@example.com",
        username="adminuser",
        full_name="Admin User",
        hashed_password=get_password_hash("adminpassword"),
        roles="admin,user",
        is_active=True,
        is_superuser=True
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(test_user):
    """Get authentication headers for test user."""
    roles_list = test_user.roles.split(",") if test_user.roles else ["user"]
    token = create_access_token(
        user_id=test_user.id,
        username=test_user.username,
        email=test_user.email,
        roles=roles_list,
        is_superuser=test_user.is_superuser
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(name="admin_auth_headers")
def admin_auth_headers_fixture(admin_user):
    """Get authentication headers for admin user."""
    roles_list = admin_user.roles.split(",") if admin_user.roles else ["user"]
    token = create_access_token(
        user_id=admin_user.id,
        username=admin_user.username,
        email=admin_user.email,
        roles=roles_list,
        is_superuser=admin_user.is_superuser
    )
    return {"Authorization": f"Bearer {token}"}


# Mock Firebase token for testing
@pytest.fixture(name="mock_firebase_token")
def mock_firebase_token_fixture():
    """Return a mock Firebase token for testing."""
    return "mock_firebase_token_12345"


@pytest.fixture(name="mock_firebase_decoded_token")
def mock_firebase_decoded_token_fixture():
    """Return a mock decoded Firebase token."""
    return {
        "uid": "firebase_uid_123",
        "email": "firebase@example.com",
        "name": "Firebase User"
    }


# Shop Owner fixture
@pytest.fixture(name="shop_owner")
def shop_owner_fixture(session):
    """Create a shop owner test user."""
    user = User(
        email="owner@example.com",
        username="shopowner",
        full_name="Shop Owner",
        hashed_password=get_password_hash("ownerpassword"),
        roles="user",
        is_active=True,
        is_superuser=False
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="owner_auth_headers")
def owner_auth_headers_fixture(shop_owner):
    """Get authentication headers for shop owner."""
    roles_list = shop_owner.roles.split(",") if shop_owner.roles else ["user"]
    token = create_access_token(
        user_id=shop_owner.id,
        username=shop_owner.username,
        email=shop_owner.email,
        roles=roles_list,
        is_superuser=shop_owner.is_superuser
    )
    return {"Authorization": f"Bearer {token}"}


# Mechanic fixture
@pytest.fixture(name="mechanic_user")
def mechanic_user_fixture(session):
    """Create a mechanic test user."""
    user = User(
        email="mechanic@example.com",
        username="mechanic",
        full_name="Test Mechanic",
        hashed_password=get_password_hash("mechanicpassword"),
        roles="user",
        is_active=True,
        is_superuser=False
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="mechanic_auth_headers")
def mechanic_auth_headers_fixture(mechanic_user):
    """Get authentication headers for mechanic."""
    roles_list = mechanic_user.roles.split(",") if mechanic_user.roles else ["user"]
    token = create_access_token(
        user_id=mechanic_user.id,
        username=mechanic_user.username,
        email=mechanic_user.email,
        roles=roles_list,
        is_superuser=mechanic_user.is_superuser
    )
    return {"Authorization": f"Bearer {token}"}


# Customer fixture
@pytest.fixture(name="customer_user")
def customer_user_fixture(session):
    """Create a customer test user."""
    user = User(
        email="customer@example.com",
        username="customer",
        full_name="Test Customer",
        hashed_password=get_password_hash("customerpassword"),
        roles="user",
        is_active=True,
        is_superuser=False
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="customer_auth_headers")
def customer_auth_headers_fixture(customer_user):
    """Get authentication headers for customer."""
    roles_list = customer_user.roles.split(",") if customer_user.roles else ["user"]
    token = create_access_token(
        user_id=customer_user.id,
        username=customer_user.username,
        email=customer_user.email,
        roles=roles_list,
        is_superuser=customer_user.is_superuser
    )
    return {"Authorization": f"Bearer {token}"}
