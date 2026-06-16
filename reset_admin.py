import sys
import os
import argparse

# Ensure the backend directory is in the Python path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from sqlmodel import Session, select
from app.db.session import engine

# Import all models to register them with SQLModel metadata registry
from app.models.user import User
from app.models.shop import Shop, UserShop
from app.models.product import Product, Service
from app.models.category import ProductCategory
from app.models.appointment import Appointment
from app.models.product_order import ProductOrder, ProductOrderItem
from app.models.invoice import Invoice, InvoiceItem, Payment
from app.models.ratings import ProductRating, ServiceRating
from app.models.customer_vehicle import CustomerVehicle
from app.models.chat import ChatRoom, ChatMessage
from app.models.notification import Notification
from app.models.quotation import Quotation, QuotationItem
from app.models.repair_progress import RepairProgress, RepairProgressUpdate
from app.models.mechanic_performance import MechanicPerformance, MechanicRating

from app.core.security import get_password_hash

def reset_admin():
    parser = argparse.ArgumentParser(description="Create or reset an Administrator user in the database.")
    parser.add_argument("--username", type=str, default=os.getenv("ADMIN_USERNAME", "admin"), help="Admin username")
    parser.add_argument("--password", type=str, default=os.getenv("ADMIN_PASSWORD", "admin123"), help="Admin password")
    parser.add_argument("--email", type=str, default=os.getenv("ADMIN_EMAIL", "admin@example.com"), help="Admin email")
    parser.add_argument("--interactive", action="store_true", help="Prompt for values interactively")

    args = parser.parse_args()

    username = args.username
    password = args.password
    email = args.email

    if args.interactive:
        print("=== Admin User Creation / Reset ===")
        user_input = input(f"Enter username [{username}]: ").strip()
        if user_input:
            username = user_input
        
        email_input = input(f"Enter email [{email}]: ").strip()
        if email_input:
            email = email_input
            
        pass_input = input(f"Enter new password [{password}]: ").strip()
        if pass_input:
            password = pass_input

    hashed_password = get_password_hash(password)

    with Session(engine) as session:
        # Check if user already exists
        statement = select(User).where(User.username == username)
        user = session.exec(statement).first()

        if user:
            print(f"Found existing user with username '{username}'. Updating to Administrator...")
            user.email = email
            user.hashed_password = hashed_password
            user.is_superuser = True
            user.roles = "admin,user"
            user.is_active = True
            session.add(user)
            action = "updated"
        else:
            print(f"User '{username}' not found. Creating new Administrator account...")
            user = User(
                username=username,
                email=email,
                hashed_password=hashed_password,
                is_superuser=True,
                roles="admin,user",
                is_active=True
            )
            session.add(user)
            action = "created"
        
        session.commit()
        print(f"\nSuccessfully {action} admin user!")
        print(f"Username: {username}")
        print(f"Email:    {email}")
        print(f"Password: {password} (hashed: {hashed_password[:10]}...)")
        print("Superuser status: True")
        print("Roles: admin,user")

if __name__ == "__main__":
    reset_admin()
