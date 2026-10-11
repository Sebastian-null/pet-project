from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from . import images, inventory, throttling
from .config import settings
from .db import get_db
from .models import Customer, Gender, Order, OrderStatus, Product, Role, Variant
from .security import current_user

router = APIRouter(prefix="/admin", tags=["CRM"])
templates = Jinja2Templates(directory="app/templates")
def auth(request: Request, db: Session):
    token = request.cookies.get("crm_token")
    if not token: raise HTTPException(status_code=401)
    class Credentials: credentials = token
    return current_user(Credentials(), db)

def administrator(request: Request, db: Session):
    """Managers run the order desk; only administrators touch the catalogue and prices."""
    user = auth(request, db)
    if user.role != Role.ADMIN: raise HTTPException(status_code=403, detail="Only administrators can change the catalogue")
    return user

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request): return templates.TemplateResponse(request, "login.html")
@router.post("/login")
def login(request: Request, email: str = Form(max_length=255), password: str = Form(max_length=128), db: Session = Depends(get_db)):
    from .models import User
    from .security import create_token, verify_password
    key = f"crm-login:{throttling.caller(request)}:{email}"
    throttling.guard(key)
    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(password, user.password_hash):
        throttling.record_attempt(key)
        return templates.TemplateResponse(request, "login.html", {"error": "Invalid email or password"}, status_code=401)
    throttling.reset(key)
    response = RedirectResponse("/admin", status_code=303)
    response.set_cookie("crm_token", create_token(user), httponly=True, samesite="lax", secure=settings.environment == "production")
    return response
@router.post("/logout")
def logout():
    response = RedirectResponse("/admin/login", status_code=303); response.delete_cookie("crm_token"); return response
@router.get("", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = auth(request, db)
    revenue = db.scalar(select(func.coalesce(func.sum(Order.total), 0)).where(Order.status != OrderStatus.CANCELLED))
    return templates.TemplateResponse(request, "dashboard.html", {"user": user, "orders": db.scalar(select(func.count(Order.id))), "customers": db.scalar(select(func.count(Customer.id))), "revenue": revenue, "low_stock": db.scalars(select(Variant).where(Variant.stock < 5).options(selectinload(Variant.product))).all()})
@router.get("/orders", response_class=HTMLResponse)
def orders(request: Request, db: Session = Depends(get_db)):
    user = auth(request, db)
    return templates.TemplateResponse(request, "orders.html", {"user": user, "orders": db.scalars(select(Order).options(selectinload(Order.customer), selectinload(Order.items)).order_by(Order.created_at.desc())).all(), "statuses": list(OrderStatus)})
@router.patch("/orders/{order_id}/status", response_class=HTMLResponse)
def change_status(order_id: int, request: Request, status: OrderStatus = Form(), db: Session = Depends(get_db)):
    auth(request, db)
    order = db.get(Order, order_id)
    if not order: raise HTTPException(404)
    if order.status == OrderStatus.CANCELLED and status != OrderStatus.CANCELLED:
        return HTMLResponse('<span class="error-note">cancelled orders cannot be reopened — the stock is already back on sale</span>', status_code=409)
    if status == OrderStatus.CANCELLED:
        inventory.cancel(db, order)
    else:
        order.status = status; db.commit()
    return HTMLResponse(f'<span class="muted">saved: {order.status.value}</span>')
# next/image only optimises the storefront's own /media files and the hosts listed in
# next.config.ts. Any other address renders as a broken product page, so it is refused
# here rather than saved and discovered later by a shopper.
ALLOWED_IMAGE_PREFIXES = ("/media/", "https://images.unsplash.com/")


def render_products(request: Request, db: Session, user, error: str | None = None, status_code: int = 200):
    products = db.scalars(select(Product).options(selectinload(Product.variants)).order_by(Product.id)).all()
    return templates.TemplateResponse(request, "products.html", {"user": user, "products": products, "error": error}, status_code=status_code)

@router.get("/products", response_class=HTMLResponse)
def product_list(request: Request, db: Session = Depends(get_db)):
    return render_products(request, db, auth(request, db))

@router.post("/products", response_class=HTMLResponse)
def create_product(request: Request, name: str = Form(), slug: str = Form(), description: str = Form(""), material: str = Form(""), image_url: str = Form(""), gender: Gender = Form(Gender.WOMEN), category: str = Form("briefs"), sku: str = Form(), size: str = Form(), color: str = Form(), price: Decimal = Form(), stock: int = Form(0), db: Session = Depends(get_db)):
    user = administrator(request, db)
    if db.scalar(select(Product).where(Product.slug == slug)):
        return render_products(request, db, user, f"Slug «{slug}» is already taken", status_code=409)
    if db.scalar(select(Variant).where(Variant.sku == sku)):
        return render_products(request, db, user, f"SKU «{sku}» is already taken", status_code=409)
    if price <= 0 or stock < 0:
        return render_products(request, db, user, "Price must be positive and stock cannot be negative", status_code=422)
    if image_url and not image_url.startswith(ALLOWED_IMAGE_PREFIXES):
        return render_products(request, db, user, "Image URL must be a /media/… path or an images.unsplash.com link", status_code=422)
    product = Product(slug=slug, name=name, description=description, material=material, image_url=image_url or None, gender=gender, category=category)
    product.variants = [Variant(sku=sku, size=size, color=color, price=price, stock=stock)]
    db.add(product); db.commit()
    return RedirectResponse("/admin/products", status_code=303)

@router.post("/products/{product_id}/image", response_class=HTMLResponse)
async def upload_product_image(product_id: int, request: Request, file: UploadFile = File(), db: Session = Depends(get_db)):
    user = administrator(request, db)
    product = db.get(Product, product_id)
    if not product: raise HTTPException(404)
    content = await images.read_capped(file)
    if content is None:
        return render_products(request, db, user, "Image must be 4 MB or smaller", status_code=413)
    extension = images.TYPES.get(images.detect(content) or "")
    if not extension:
        return render_products(request, db, user, "Only JPEG, PNG or WebP images are accepted", status_code=415)
    previous = product.image_url
    product.image_url = images.store(content, f"product-{product.slug}", extension)
    images.remove(previous)
    db.commit()
    return RedirectResponse("/admin/products", status_code=303)

@router.post("/products/{product_id}/variants", response_class=HTMLResponse)
def add_variant(product_id: int, request: Request, sku: str = Form(), size: str = Form(), color: str = Form(), price: Decimal = Form(), stock: int = Form(0), db: Session = Depends(get_db)):
    user = administrator(request, db)
    product = db.get(Product, product_id)
    if not product: raise HTTPException(404)
    if db.scalar(select(Variant).where(Variant.sku == sku)):
        return render_products(request, db, user, f"SKU «{sku}» is already taken", status_code=409)
    if any(variant.size == size and variant.color == color for variant in product.variants):
        return render_products(request, db, user, f"{product.name} already has {color} / {size}", status_code=409)
    if price <= 0 or stock < 0:
        return render_products(request, db, user, "Price must be positive and stock cannot be negative", status_code=422)
    db.add(Variant(product_id=product.id, sku=sku, size=size, color=color, price=price, stock=stock)); db.commit()
    return RedirectResponse("/admin/products", status_code=303)

@router.patch("/variants/{variant_id}", response_class=HTMLResponse)
def update_variant(variant_id: int, request: Request, price: Decimal = Form(), stock: int = Form(), db: Session = Depends(get_db)):
    administrator(request, db)
    variant = db.get(Variant, variant_id)
    if not variant: raise HTTPException(404)
    if price <= 0 or stock < 0: raise HTTPException(status_code=422, detail="Price must be positive and stock cannot be negative")
    variant.price, variant.stock = price, stock
    db.commit()
    return templates.TemplateResponse(request, "_variant.html", {"variant": variant, "saved": True})

@router.post("/products/{product_id}/visibility")
def toggle_visibility(product_id: int, request: Request, db: Session = Depends(get_db)):
    administrator(request, db)
    product = db.get(Product, product_id)
    if not product: raise HTTPException(404)
    product.is_active = not product.is_active
    db.commit()
    return RedirectResponse("/admin/products", status_code=303)
