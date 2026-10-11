import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import stripe
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi import Path as FastPath
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from . import images, payments, throttling
from .config import settings
from .db import get_db
from .mailer import send_verification_code
from .models import (
    Customer,
    EmailVerification,
    Gender,
    Order,
    OrderItem,
    Product,
    User,
    Variant,
)
from .schemas import (
    CheckoutIn,
    CheckoutOut,
    CustomerProfileIn,
    CustomerProfileOut,
    CustomerRegisterIn,
    CustomerTokenOut,
    LoginIn,
    OrderOut,
    OrderSummaryOut,
    PasswordChangeIn,
    ProductOut,
    TokenOut,
    VerificationConfirmIn,
    VerificationRequestOut,
)
from .security import (
    create_customer_token,
    create_token,
    current_customer,
    current_user,
    optional_customer,
    password_hash,
    verification_code_hash,
    verify_password,
)

router = APIRouter(prefix="/api/v1")

@router.get("/products", response_model=list[ProductOut])
def products(q: str | None = Query(default=None, max_length=80), gender: Gender | None = None, category: str | None = None, size: str | None = None, color: str | None = None, min_price: float | None = None, max_price: float | None = None, db: Session = Depends(get_db)):
    query = select(Product).where(Product.is_active.is_(True))
    if q:
        query = query.where(Product.name.ilike(f"%{q}%"))
    if gender: query = query.where(Product.gender == gender)
    if category: query = query.where(Product.category == category)
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
    active = select(Product.id).where(Product.is_active.is_(True)).scalar_subquery()
    sizes = db.scalars(select(Variant.size).where(Variant.product_id.in_(active)).distinct().order_by(Variant.size)).all()
    colors = db.scalars(select(Variant.color).where(Variant.product_id.in_(active)).distinct().order_by(Variant.color)).all()
    categories = db.scalars(select(Product.category).where(Product.is_active.is_(True)).distinct().order_by(Product.category)).all()
    return {"sizes": sizes, "colors": colors, "categories": categories}

@router.get("/products/{slug}", response_model=ProductOut)
def product(slug: str = FastPath(pattern=r"^[a-z0-9-]{1,160}$"), db: Session = Depends(get_db)):
    item = db.scalar(select(Product).where(Product.slug == slug, Product.is_active.is_(True)).options(selectinload(Product.variants)))
    if not item: raise HTTPException(status_code=404, detail="Product not found")
    return item

@router.post("/auth/login", response_model=TokenOut)
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)):
    key = f"admin-login:{throttling.caller(request)}:{payload.email}"
    throttling.guard(key)
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        throttling.record_attempt(key)
        raise HTTPException(status_code=401, detail="Invalid email or password")
    throttling.reset(key)
    return TokenOut(access_token=create_token(user), role=user.role)

@router.post("/auth/register/request-code", response_model=VerificationRequestOut, status_code=status.HTTP_202_ACCEPTED)
def request_registration_code(payload: CustomerRegisterIn, request: Request, db: Session = Depends(get_db)):
    key = f"register:{throttling.caller(request)}"
    throttling.guard(key); throttling.record_attempt(key)
    if db.scalar(select(Customer).where(Customer.email == payload.email)):
        raise HTTPException(status_code=409, detail="Email is already registered")
    db.query(EmailVerification).filter(EmailVerification.email == payload.email).delete()
    code = f"{secrets.randbelow(1_000_000):06d}"
    verification = EmailVerification(email=payload.email, name=payload.name, password_hash=password_hash(payload.password), code_hash=verification_code_hash(payload.email, code), expires_at=datetime.now(UTC) + timedelta(minutes=10))
    db.add(verification); db.commit()
    send_verification_code(payload.email, code)
    return VerificationRequestOut(message="Verification code sent", debug_code=code if settings.environment == "development" else None)

@router.post("/auth/register/confirm", response_model=CustomerTokenOut, status_code=status.HTTP_201_CREATED)
def confirm_registration(payload: VerificationConfirmIn, db: Session = Depends(get_db)):
    verification = db.scalar(select(EmailVerification).where(EmailVerification.email == payload.email).order_by(EmailVerification.created_at.desc()))
    if not verification or verification.expires_at < datetime.now(UTC):
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
def customer_login(payload: LoginIn, request: Request, db: Session = Depends(get_db)):
    key = f"login:{throttling.caller(request)}:{payload.email}"
    throttling.guard(key)
    customer = db.scalar(select(Customer).where(Customer.email == payload.email))
    if not customer or not customer.password_hash or not verify_password(payload.password, customer.password_hash):
        throttling.record_attempt(key)
        raise HTTPException(status_code=401, detail="Invalid email or password")
    throttling.reset(key)
    return CustomerTokenOut(access_token=create_customer_token(customer), email=customer.email)

@router.get("/account", response_model=CustomerProfileOut)
def account(customer: Customer = Depends(current_customer)):
    return customer

@router.patch("/account", response_model=CustomerProfileOut)
def update_account(payload: CustomerProfileIn, customer: Customer = Depends(current_customer), db: Session = Depends(get_db)):
    changes = payload.model_dump(exclude_unset=True)
    # Phone and birth date are nullable, name is not: an explicit "name": null used to
    # reach the database and surface as a 500 instead of a validation error.
    if changes.get("name", "") is None: raise HTTPException(status_code=422, detail="Name cannot be empty")
    for field, value in changes.items(): setattr(customer, field, value)
    db.commit(); db.refresh(customer)
    return customer

@router.get("/account/orders", response_model=list[OrderSummaryOut])
def account_orders(customer: Customer = Depends(current_customer), db: Session = Depends(get_db)):
    return db.scalars(select(Order).where(Order.customer_id == customer.id).options(selectinload(Order.items)).order_by(Order.created_at.desc())).all()

@router.post("/account/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(payload: PasswordChangeIn, request: Request, customer: Customer = Depends(current_customer), db: Session = Depends(get_db)):
    key = f"password:{throttling.caller(request)}:{customer.id}"
    throttling.guard(key)
    if not customer.password_hash: raise HTTPException(status_code=409, detail="This account has no password yet; register to set one")
    if not verify_password(payload.current_password, customer.password_hash):
        throttling.record_attempt(key)
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    throttling.reset(key)
    customer.password_hash = password_hash(payload.new_password)
    db.commit()

@router.post("/account/avatar", response_model=CustomerProfileOut)
async def upload_avatar(file: UploadFile = File(), customer: Customer = Depends(current_customer), db: Session = Depends(get_db)):
    content = await images.read_capped(file)
    if content is None: raise HTTPException(status_code=413, detail="Image must be 4 MB or smaller")
    extension = images.TYPES.get(images.detect(content) or "")
    if not extension: raise HTTPException(status_code=415, detail="Only JPEG, PNG or WebP images are accepted")
    previous = customer.avatar_url
    customer.avatar_url = images.store(content, f"avatar-{customer.id}", extension)
    images.remove(previous)
    db.commit(); db.refresh(customer)
    return customer

@router.post("/orders", response_model=CheckoutOut, status_code=status.HTTP_201_CREATED)
def checkout(payload: CheckoutIn, db: Session = Depends(get_db), signed_in: Customer | None = Depends(optional_customer)):
    # SELECT ... FOR UPDATE prevents two checkouts from selling the same last unit.
    try:
        lookup = Customer.id == signed_in.id if signed_in else Customer.email == payload.email
        customer = db.scalar(select(Customer).where(lookup).with_for_update())
        # A guest may not check out under an email that already has a password. Without
        # this, anyone could overwrite a registered shopper's name and phone and push
        # orders into their account just by typing their address into the form.
        if customer is not None and not signed_in and customer.password_hash:
            raise HTTPException(status_code=401, detail="This email already has an account — please sign in to continue")
        if not customer:
            customer = Customer(email=payload.email, name=payload.name, phone=payload.phone); db.add(customer); db.flush()
        else: customer.name, customer.phone = payload.name, payload.phone
        order = Order(customer=customer, delivery_address=payload.delivery_address); db.add(order)
        total = Decimal("0")
        for line in payload.items:
            variant = db.scalar(select(Variant).where(Variant.id == line.variant_id).with_for_update())
            if not variant or not variant.product.is_active: raise HTTPException(status_code=422, detail="Product variant not found")
            if variant.stock < line.quantity: raise HTTPException(status_code=409, detail=f"Not enough stock: {variant.sku}")
            variant.stock -= line.quantity
            total += variant.price * line.quantity
            order.items.append(OrderItem(variant=variant, title=f"{variant.product.name}, {variant.color} / {variant.size}", quantity=line.quantity, unit_price=variant.price))
        order.total = total; db.commit(); db.refresh(order)
    except HTTPException:
        db.rollback(); raise
    except Exception:
        db.rollback(); raise
    if not payments.enabled(): return CheckoutOut.model_validate(order)
    try:
        payment_url = payments.create_checkout_session(order, payload.locale)
        db.commit()
    except stripe.StripeError:
        db.rollback(); payments.release(db, order)
        raise HTTPException(status_code=502, detail="Payment provider is unavailable") from None
    result = CheckoutOut.model_validate(order); result.payment_url = payment_url
    return result

@router.get("/orders/{order_id}", response_model=OrderOut)
def order(order_id: int, _user=Depends(current_user), db: Session = Depends(get_db)):
    item = db.scalar(select(Order).where(Order.id == order_id).options(selectinload(Order.items)))
    if not item: raise HTTPException(status_code=404, detail="Order not found")
    return item
