from decimal import Decimal
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from .db import get_db
from .models import Customer, Order, OrderStatus, Product, Variant
from .security import current_user

router = APIRouter(prefix="/admin", tags=["CRM"])
templates = Jinja2Templates(directory="app/templates")
def auth(request: Request, db: Session):
    token = request.cookies.get("crm_token")
    if not token: raise HTTPException(status_code=401)
    class Credentials: credentials = token
    return current_user(Credentials(), db)

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request): return templates.TemplateResponse(request, "login.html")
@router.post("/login")
def login(request: Request, email: str = Form(), password: str = Form(), db: Session = Depends(get_db)):
    from .models import User
    from .security import create_token, verify_password
    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(password, user.password_hash): return templates.TemplateResponse(request, "login.html", {"error": "Invalid email or password"}, status_code=401)
    response = RedirectResponse("/admin", status_code=303); response.set_cookie("crm_token", create_token(user), httponly=True, samesite="lax"); return response
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
    auth(request, db); order = db.get(Order, order_id)
    if not order: raise HTTPException(404)
    order.status = status; db.commit(); return HTMLResponse(f'<span class="status">{status.value}</span>')
@router.get("/products", response_class=HTMLResponse)
def product_list(request: Request, db: Session = Depends(get_db)):
    user = auth(request, db)
    return templates.TemplateResponse(request, "products.html", {"user": user, "products": db.scalars(select(Product).options(selectinload(Product.variants))).all()})
