from pydantic import BaseModel, EmailStr, Field
from .models import OrderStatus, Role

class VariantOut(BaseModel):
    id: int; sku: str; size: str; color: str; price: float; stock: int
    model_config = {"from_attributes": True}
class ProductOut(BaseModel):
    id: int; slug: str; name: str; description: str; material: str; image_url: str | None; variants: list[VariantOut]
    model_config = {"from_attributes": True}
class CartItemIn(BaseModel): variant_id: int; quantity: int = Field(gt=0, le=20)
class CheckoutIn(BaseModel):
    email: EmailStr; name: str = Field(min_length=2, max_length=160); phone: str | None = None; delivery_address: str = Field(min_length=8); items: list[CartItemIn] = Field(min_length=1)
class OrderItemOut(BaseModel):
    title: str; quantity: int; unit_price: float
    model_config = {"from_attributes": True}
class OrderOut(BaseModel):
    id: int; status: OrderStatus; total: float; delivery_address: str; items: list[OrderItemOut]
    model_config = {"from_attributes": True}
class LoginIn(BaseModel): email: EmailStr; password: str
class CustomerRegisterIn(LoginIn): name: str = Field(min_length=2, max_length=160)
class VerificationRequestOut(BaseModel): message: str; debug_code: str | None = None
class VerificationConfirmIn(BaseModel): email: EmailStr; code: str = Field(pattern=r"^\d{6}$")
class TokenOut(BaseModel): access_token: str; token_type: str = "bearer"; role: Role
class CustomerTokenOut(BaseModel): access_token: str; token_type: str = "bearer"; email: EmailStr
