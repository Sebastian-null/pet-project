from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from .models import Gender, OrderStatus, Role


class VariantOut(BaseModel):
    id: int; sku: str; size: str; color: str; price: float; stock: int
    model_config = {"from_attributes": True}
class ProductOut(BaseModel):
    id: int; slug: str; name: str; description: str; material: str; image_url: str | None; gender: Gender; category: str; variants: list[VariantOut]
    model_config = {"from_attributes": True}
class CartItemIn(BaseModel): variant_id: int; quantity: int = Field(gt=0, le=20)
class CheckoutIn(BaseModel):
    email: EmailStr; name: str = Field(min_length=2, max_length=160); phone: str | None = Field(default=None, max_length=32); delivery_address: str = Field(min_length=8, max_length=500); items: list[CartItemIn] = Field(min_length=1, max_length=20); locale: str = Field(default="uk", pattern="^(uk|en)$")
class OrderItemOut(BaseModel):
    title: str; quantity: int; unit_price: float
    model_config = {"from_attributes": True}
class OrderOut(BaseModel):
    id: int; status: OrderStatus; total: float; delivery_address: str; items: list[OrderItemOut]
    model_config = {"from_attributes": True}
class CheckoutOut(OrderOut): payment_url: str | None = None
class OrderSummaryOut(BaseModel):
    id: int; status: OrderStatus; total: float; created_at: datetime; items: list[OrderItemOut]
    model_config = {"from_attributes": True}
class PaymentStatusOut(BaseModel): order_id: int; status: OrderStatus; total: float
# The length cap bounds the work bcrypt is asked to do; the floor belongs on
# registration only, so signing in never leaks the current password policy.
class LoginIn(BaseModel): email: EmailStr; password: str = Field(max_length=128)
class CustomerRegisterIn(LoginIn):
    name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=8, max_length=128)
class VerificationRequestOut(BaseModel): message: str; debug_code: str | None = None
class VerificationConfirmIn(BaseModel): email: EmailStr; code: str = Field(pattern=r"^\d{6}$")
class TokenOut(BaseModel): access_token: str; token_type: str = "bearer"; role: Role
class CustomerTokenOut(BaseModel): access_token: str; token_type: str = "bearer"; email: EmailStr
class CustomerProfileOut(BaseModel):
    email: EmailStr; name: str; phone: str | None; birth_date: date | None; avatar_url: str | None
    model_config = {"from_attributes": True}
class PasswordChangeIn(BaseModel): current_password: str = Field(max_length=128); new_password: str = Field(min_length=8, max_length=128)
class CustomerProfileIn(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160); phone: str | None = Field(default=None, max_length=32); birth_date: date | None = None

    @field_validator("birth_date")
    @classmethod
    def must_be_in_the_past(cls, value: date | None) -> date | None:
        if value and value >= date.today(): raise ValueError("Birth date must be in the past")
        return value
