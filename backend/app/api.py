from datetime import datetime, timedelta, timezone
import secrets
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from .db import get_db
from .models import Customer, EmailVerification, Order, OrderItem, Product, User, Variant
from .schemas import CheckoutIn, CustomerRegisterIn, CustomerTokenOut, LoginIn, OrderOut, ProductOut, TokenOut, VerificationConfirmIn, VerificationRequestOut
from .security import create_customer_token, create_token, current_user, password_hash, verification_code_hash, verify_password
from .mailer import send_verification_code

router = APIRouter(prefix="/api/v1")

@router.get("/products", response_model=list[ProductOut])
def products(q: str | None = None, size: str | None = None, color: str | None = None, min_price: float | None = None, max_price: float | None = None, db: Session = Depends(get_db)):
    query = select(Product).where(Product.is_active.is_(True))
    if q:
        query = query.where(Product.name.ilike(f"%{q}%"))
    if size or color or min_price is not None or max_price is not None:
        query = query.join(Product.variants)
        if size: query = query.where(Variant.size == size)
        if color: query = query.where(Variant.color == color)
        if min_price is not None: query = query.where(Variant.price >= min_price)
        if max_price is not None: query = query.where(Variant.price <= max_price)
        query = query.distinct()
    return db.scalars(query.options(selectinload(Product.variants)).order_by(Product.id.desc())).all()

@router.get("/products/filters")
def product_filters(db: Session = Depends(get_db)):
    sizes = db.scalars(select(Variant.size).distinct().order_by(Variant.size)).all()
    colors = db.scalars(select(Variant.color).distinct().order_by(Variant.color)).all()
    return {"sizes": sizes, "colors": colors}

@router.get("/products/{slug}", response_model=ProductOut)
def product(slug: str, db: Session = Depends(get_db)):
    item = db.scalar(select(Product).where(Product.slug == slug, Product.is_active.is_(True)).options(selectinload(Product.variants)))
    if not item: raise HTTPException(status_code=404, detail="Product not found")
    return item

@router.post("/auth/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash): raise HTTPException(status_code=401, detail="Invalid email or password")
    return TokenOut(access_token=create_token(user), role=user.role)

@router.post("/auth/register/request-code", response_model=VerificationRequestOut, status_code=status.HTTP_202_ACCEPTED)
def request_registration_code(payload: CustomerRegisterIn, db: Session = Depends(get_db)):
    if db.scalar(select(Customer).where(Customer.email == payload.email)):
        raise HTTPException(status_code=409, detail="Email is already registered")
    db.query(EmailVerification).filter(EmailVerification.email == payload.email).delete()
    code = f"{secrets.randbelow(1_000_000):06d}"
    verification = EmailVerification(email=payload.email, name=payload.name, password_hash=password_hash(payload.password), code_hash=verification_code_hash(payload.email, code), expires_at=datetime.now(timezone.utc) + timedelta(minutes=10))
    db.add(verification); db.commit()
    send_verification_code(payload.email, code)
    from .config import settings
    return VerificationRequestOut(message="Verification code sent", debug_code=code if settings.environment == "development" else None)

@router.post("/auth/register/confirm", response_model=CustomerTokenOut, status_code=status.HTTP_201_CREATED)
def confirm_registration(payload: VerificationConfirmIn, db: Session = Depends(get_db)):
    verification = db.scalar(select(EmailVerification).where(EmailVerification.email == payload.email).order_by(EmailVerification.created_at.desc()))
    if not verification or verification.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Verification code expired")
    if verification.attempts >= 5:
        raise HTTPException(status_code=429, detail="Too many attempts; request a new code")
    verification.attempts += 1
    if not secrets.compare_digest(verification.code_hash, verification_code_hash(payload.email, payload.code)):
        db.commit(); raise HTTPException(status_code=400, detail="Invalid verification code")
    customer = Customer(email=verification.email, name=verification.name, password_hash=verification.password_hash)
    db.add(customer); db.delete(verification); db.commit(); db.refresh(customer)
    return CustomerTokenOut(access_token=create_customer_token(customer), email=customer.email)

@router.post("/auth/customer/login", response_model=CustomerTokenOut)
def customer_login(payload: LoginIn, db: Session = Depends(get_db)):
    customer = db.scalar(select(Customer).where(Customer.email == payload.email))
    if not customer or not customer.password_hash or not verify_password(payload.password, customer.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return CustomerTokenOut(access_token=create_customer_token(customer), email=customer.email)

@router.post("/orders", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def checkout(payload: CheckoutIn, db: Session = Depends(get_db)):
    # SELECT ... FOR UPDATE prevents two checkouts from selling the same last unit.
    try:
        customer = db.scalar(select(Customer).where(Customer.email == payload.email).with_for_update())
        if not customer:
            customer = Customer(email=payload.email, name=payload.name, phone=payload.phone); db.add(customer); db.flush()
        else: customer.name, customer.phone = payload.name, payload.phone
        order = Order(customer=customer, delivery_address=payload.delivery_address); db.add(order)
        total = Decimal("0")
        for line in payload.items:
            variant = db.scalar(select(Variant).where(Variant.id == line.variant_id).with_for_update())
            if not variant: raise HTTPException(status_code=422, detail="Product variant not found")
            if variant.stock < line.quantity: raise HTTPException(status_code=409, detail=f"Not enough stock: {variant.sku}")
            variant.stock -= line.quantity
            total += variant.price * line.quantity
            order.items.append(OrderItem(variant=variant, title=f"{variant.product.name}, {variant.color} / {variant.size}", quantity=line.quantity, unit_price=variant.price))
        order.total = total; db.commit(); db.refresh(order)
        return order
    except HTTPException:
        db.rollback(); raise
    except Exception:
        db.rollback(); raise

@router.get("/orders/{order_id}", response_model=OrderOut)
def order(order_id: int, _user=Depends(current_user), db: Session = Depends(get_db)):
    item = db.scalar(select(Order).where(Order.id == order_id).options(selectinload(Order.items)))
    if not item: raise HTTPException(status_code=404, detail="Order not found")
    return item
