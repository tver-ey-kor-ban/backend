"""Invoice endpoints for billing and payments."""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.db import get_session
from app.models.invoice import (
    Invoice, InvoiceItem, Payment, InvoiceCreate, InvoiceRead,
    PaymentCreate, InvoiceStatus
)
from app.models.user import User
from app.core.security import get_current_user, TokenData
from app.services.shop_service import ShopService
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/invoices", tags=["invoices"])


def generate_invoice_number(shop_id: int, session: Session) -> str:
    """Generate a unique invoice number."""
    from sqlalchemy import func
    count = session.exec(
        select(func.count(Invoice.id)).where(Invoice.shop_id == shop_id)
    ).one()
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    return f"INV-{shop_id}-{timestamp}-{count + 1:04d}"


# ==================== SHOP: CREATE/MANAGE INVOICES ====================

@router.post("/shops/{shop_id}", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
def create_invoice(
    shop_id: int,
    invoice_data: InvoiceCreate,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Create a new invoice (Shop owner/mechanic only)."""
    shop_service = ShopService(session)
    
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop members can create invoices"
        )
    
    # Generate invoice number if not provided
    invoice_number = invoice_data.invoice_number or generate_invoice_number(shop_id, session)
    
    # Check for duplicate invoice number
    existing = session.exec(
        select(Invoice).where(Invoice.invoice_number == invoice_number)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice number already exists"
        )
    
    # Create invoice
    invoice = Invoice(
        shop_id=shop_id,
        customer_id=invoice_data.customer_id,
        appointment_id=invoice_data.appointment_id,
        product_order_id=invoice_data.product_order_id,
        quotation_id=invoice_data.quotation_id,
        invoice_number=invoice_number,
        labor_cost=invoice_data.labor_cost or 0.0,
        parts_cost=invoice_data.parts_cost or 0.0,
        service_cost=invoice_data.service_cost or 0.0,
        tax_amount=invoice_data.tax_amount or 0.0,
        discount_amount=invoice_data.discount_amount or 0.0,
        total_amount=invoice_data.total_amount,
        due_date=invoice_data.due_date or (datetime.utcnow() + timedelta(days=7)),
        status=InvoiceStatus.DRAFT
    )
    session.add(invoice)
    session.flush()
    
    # Create invoice items
    for item_data in invoice_data.items:
        total_price = item_data.quantity * item_data.unit_price
        item = InvoiceItem(
            invoice_id=invoice.id,
            item_type=item_data.item_type,
            name=item_data.name,
            description=item_data.description,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            total_price=total_price
        )
        session.add(item)
    
    session.commit()
    session.refresh(invoice)
    
    return invoice


@router.get("/shops/{shop_id}", response_model=List[InvoiceRead])
def get_shop_invoices(
    shop_id: int,
    status: Optional[InvoiceStatus] = None,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get all invoices for a shop (Shop owner/mechanic only)."""
    shop_service = ShopService(session)
    
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop members can view invoices"
        )
    
    query = select(Invoice).where(Invoice.shop_id == shop_id)
    
    if status:
        query = query.where(Invoice.status == status)
    
    query = query.order_by(Invoice.created_at.desc())
    invoices = session.exec(query).all()
    
    # Load items and payments for each invoice
    result = []
    for inv in invoices:
        items = session.exec(
            select(InvoiceItem).where(InvoiceItem.invoice_id == inv.id)
        ).all()
        payments = session.exec(
            select(Payment).where(Payment.invoice_id == inv.id)
        ).all()
        
        result.append({
            "id": inv.id,
            "shop_id": inv.shop_id,
            "customer_id": inv.customer_id,
            "appointment_id": inv.appointment_id,
            "product_order_id": inv.product_order_id,
            "quotation_id": inv.quotation_id,
            "invoice_number": inv.invoice_number,
            "status": inv.status,
            "labor_cost": inv.labor_cost,
            "parts_cost": inv.parts_cost,
            "service_cost": inv.service_cost,
            "tax_amount": inv.tax_amount,
            "discount_amount": inv.discount_amount,
            "total_amount": inv.total_amount,
            "amount_paid": inv.amount_paid,
            "due_date": inv.due_date,
            "created_at": inv.created_at,
            "updated_at": inv.updated_at,
            "paid_at": inv.paid_at,
            "items": items,
            "payments": payments
        })
    
    return result


@router.get("/shops/{shop_id}/{invoice_id}")
def get_invoice_detail(
    shop_id: int,
    invoice_id: int,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get invoice details (Shop owner/mechanic only)."""
    shop_service = ShopService(session)
    
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop members can view invoices"
        )
    
    invoice = session.exec(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.shop_id == shop_id
        )
    ).first()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    items = session.exec(
        select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id)
    ).all()
    payments = session.exec(
        select(Payment).where(Payment.invoice_id == invoice.id)
    ).all()
    
    customer = session.get(User, invoice.customer_id)
    
    return {
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "customer": {
            "id": invoice.customer_id,
            "name": customer.full_name if customer else "Unknown",
            "email": customer.email if customer else None
        },
        "appointment_id": invoice.appointment_id,
        "product_order_id": invoice.product_order_id,
        "quotation_id": invoice.quotation_id,
        "status": invoice.status,
        "labor_cost": invoice.labor_cost,
        "parts_cost": invoice.parts_cost,
        "service_cost": invoice.service_cost,
        "tax_amount": invoice.tax_amount,
        "discount_amount": invoice.discount_amount,
        "total_amount": invoice.total_amount,
        "amount_paid": invoice.amount_paid,
        "balance_due": invoice.total_amount - invoice.amount_paid,
        "due_date": invoice.due_date,
        "created_at": invoice.created_at,
        "updated_at": invoice.updated_at,
        "paid_at": invoice.paid_at,
        "items": items,
        "payments": payments
    }


@router.post("/shops/{shop_id}/{invoice_id}/send")
def send_invoice(
    shop_id: int,
    invoice_id: int,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Send invoice to customer (changes status to SENT)."""
    shop_service = ShopService(session)
    notification_service = NotificationService(session)
    
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop members can send invoices"
        )
    
    invoice = session.exec(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.shop_id == shop_id
        )
    ).first()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    if invoice.status != InvoiceStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot send invoice with status: {invoice.status}"
        )
    
    invoice.status = InvoiceStatus.SENT
    invoice.updated_at = datetime.utcnow()
    session.commit()
    
    # Notify customer
    from app.models.notification import NotificationType
    notification_service.create_notification(
        user_id=invoice.customer_id,
        type=NotificationType.STATUS_UPDATE,
        title="New Invoice Received",
        message=f"You have received invoice #{invoice.invoice_number} - Total: ${invoice.total_amount:.2f}",
        data={
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "total_amount": invoice.total_amount,
            "due_date": invoice.due_date.isoformat() if invoice.due_date else None
        }
    )
    
    return {
        "message": "Invoice sent to customer",
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "status": invoice.status
    }


@router.post("/shops/{shop_id}/{invoice_id}/payments")
def record_payment(
    shop_id: int,
    invoice_id: int,
    payment_data: PaymentCreate,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Record a payment for an invoice (Shop only)."""
    shop_service = ShopService(session)
    notification_service = NotificationService(session)
    
    if not shop_service.is_shop_member(current_user.user_id, shop_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shop members can record payments"
        )
    
    invoice = session.exec(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.shop_id == shop_id
        )
    ).first()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    if invoice.status in [InvoiceStatus.PAID, InvoiceStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot record payment for invoice with status: {invoice.status}"
        )
    
    # Create payment record
    payment = Payment(
        invoice_id=invoice.id,
        amount=payment_data.amount,
        method=payment_data.method,
        reference=payment_data.reference,
        notes=payment_data.notes
    )
    session.add(payment)
    
    # Update invoice
    invoice.amount_paid += payment_data.amount
    
    if invoice.amount_paid >= invoice.total_amount:
        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = datetime.utcnow()
    elif invoice.amount_paid > 0:
        invoice.status = InvoiceStatus.PARTIALLY_PAID
    
    invoice.updated_at = datetime.utcnow()
    session.commit()
    
    # Notify customer
    from app.models.notification import NotificationType
    balance = invoice.total_amount - invoice.amount_paid
    
    notification_service.create_notification(
        user_id=invoice.customer_id,
        type=NotificationType.STATUS_UPDATE,
        title="Payment Received",
        message=f"Payment of ${payment_data.amount:.2f} received for invoice #{invoice.invoice_number}. Balance: ${balance:.2f}",
        data={
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "payment_amount": payment_data.amount,
            "balance_due": balance
        }
    )
    
    return {
        "message": "Payment recorded successfully",
        "invoice_id": invoice.id,
        "payment_amount": payment_data.amount,
        "amount_paid": invoice.amount_paid,
        "balance_due": balance,
        "status": invoice.status
    }


# ==================== CUSTOMER: VIEW/PAY INVOICES ====================

@router.get("/my-invoices")
def get_my_invoices(
    status: Optional[InvoiceStatus] = None,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get all invoices for logged-in customer."""
    query = select(Invoice).where(Invoice.customer_id == current_user.user_id)
    
    if status:
        query = query.where(Invoice.status == status)
    
    query = query.order_by(Invoice.created_at.desc())
    invoices = session.exec(query).all()
    
    result = []
    for inv in invoices:
        items = session.exec(
            select(InvoiceItem).where(InvoiceItem.invoice_id == inv.id)
        ).all()
        payments = session.exec(
            select(Payment).where(Payment.invoice_id == inv.id)
        ).all()
        
        # Get shop info
        from app.models.shop import Shop
        shop = session.get(Shop, inv.shop_id)
        
        result.append({
            "id": inv.id,
            "shop": {
                "id": inv.shop_id,
                "name": shop.name if shop else "Unknown"
            },
            "invoice_number": inv.invoice_number,
            "appointment_id": inv.appointment_id,
            "product_order_id": inv.product_order_id,
            "status": inv.status,
            "total_amount": inv.total_amount,
            "amount_paid": inv.amount_paid,
            "balance_due": inv.total_amount - inv.amount_paid,
            "due_date": inv.due_date,
            "created_at": inv.created_at,
            "paid_at": inv.paid_at,
            "items": items,
            "payments": payments
        })
    
    return result


@router.get("/my-invoices/{invoice_id}")
def get_my_invoice_detail(
    invoice_id: int,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get specific invoice details for customer."""
    invoice = session.exec(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.customer_id == current_user.user_id
        )
    ).first()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    items = session.exec(
        select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id)
    ).all()
    payments = session.exec(
        select(Payment).where(Payment.invoice_id == invoice.id)
    ).all()
    
    # Get shop info
    from app.models.shop import Shop
    shop = session.get(Shop, invoice.shop_id)
    
    return {
        "id": invoice.id,
        "shop": {
            "id": invoice.shop_id,
            "name": shop.name if shop else "Unknown",
            "address": shop.address if shop else None,
            "phone": shop.phone if shop else None
        },
        "invoice_number": invoice.invoice_number,
        "appointment_id": invoice.appointment_id,
        "product_order_id": invoice.product_order_id,
        "status": invoice.status,
        "labor_cost": invoice.labor_cost,
        "parts_cost": invoice.parts_cost,
        "service_cost": invoice.service_cost,
        "tax_amount": invoice.tax_amount,
        "discount_amount": invoice.discount_amount,
        "total_amount": invoice.total_amount,
        "amount_paid": invoice.amount_paid,
        "balance_due": invoice.total_amount - invoice.amount_paid,
        "due_date": invoice.due_date,
        "created_at": invoice.created_at,
        "updated_at": invoice.updated_at,
        "paid_at": invoice.paid_at,
        "items": items,
        "payments": payments
    }
