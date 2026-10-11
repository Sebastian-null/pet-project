import hashlib
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import Customer, User

bearer = HTTPBearer(auto_error=False)
def _password_bytes(value: str) -> bytes:
    # bcrypt reads at most 72 bytes; truncating keeps hashes written by earlier releases valid.
    return value.encode()[:72]
def password_hash(value: str) -> str: return bcrypt.hashpw(_password_bytes(value), bcrypt.gensalt()).decode()
def verify_password(value: str, hashed: str) -> bool: return bcrypt.checkpw(_password_bytes(value), hashed.encode())
def verification_code_hash(email: str, code: str) -> str:
    return hashlib.sha256(f"{email.lower()}:{code}:{settings.jwt_secret}".encode()).hexdigest()
def create_token(user: User) -> str:
    # "kind" keeps staff and customer tokens apart: both carry a numeric id, so without
    # it a customer token would authenticate as the staff member with the same id.
    payload = {"sub": str(user.id), "kind": "staff", "role": user.role.value, "exp": datetime.now(UTC) + timedelta(hours=8)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
def create_customer_token(customer: Customer) -> str:
    payload = {"sub": str(customer.id), "kind": "customer", "exp": datetime.now(UTC) + timedelta(days=14)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
def _subject(token: str, kind: str) -> int:
    """Return the id a token belongs to, refusing anything we did not mint ourselves.

    "sub" is parsed defensively: a token signed with our secret but carrying a missing
    or non-numeric subject must read as "not authenticated", never as a server error.
    """
    try: payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except Exception: raise HTTPException(status_code=401, detail="Invalid token") from None
    if payload.get("kind") != kind: raise HTTPException(status_code=401, detail="Invalid token")
    try: return int(payload["sub"])
    except (KeyError, TypeError, ValueError): raise HTTPException(status_code=401, detail="Invalid token") from None
def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not credentials: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    user = db.get(User, _subject(credentials.credentials, "staff"))
    if not user: raise HTTPException(status_code=401, detail="User not found")
    return user
def current_customer(credentials: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)) -> Customer:
    if not credentials: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    customer = db.get(Customer, _subject(credentials.credentials, "customer"))
    if not customer: raise HTTPException(status_code=401, detail="Customer not found")
    return customer
def optional_customer(credentials: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)) -> Customer | None:
    """Checkout works for guests, but links the order to the account when one is signed in."""
    if not credentials: return None
    try: return current_customer(credentials, db)
    except HTTPException: return None
