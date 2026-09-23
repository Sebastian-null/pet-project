from datetime import datetime, timedelta, timezone
import jwt
import hashlib
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from .config import settings
from .db import get_db
from .models import Role, User

crypt = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)
def password_hash(value: str) -> str: return crypt.hash(value)
def verify_password(value: str, hashed: str) -> bool: return crypt.verify(value, hashed)
def verification_code_hash(email: str, code: str) -> str:
    return hashlib.sha256(f"{email.lower()}:{code}:{settings.jwt_secret}".encode()).hexdigest()
def create_token(user: User) -> str:
    payload = {"sub": str(user.id), "role": user.role.value, "exp": datetime.now(timezone.utc) + timedelta(hours=8)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
def create_customer_token(customer: "Customer") -> str:
    payload = {"sub": str(customer.id), "kind": "customer", "exp": datetime.now(timezone.utc) + timedelta(days=14)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not credentials: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try: user_id = int(jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])["sub"])
    except Exception: raise HTTPException(status_code=401, detail="Invalid token")
    user = db.get(User, user_id)
    if not user: raise HTTPException(status_code=401, detail="User not found")
    return user
def admin_only(user: User = Depends(current_user)) -> User:
    if user.role != Role.ADMIN: raise HTTPException(status_code=403, detail="Administrator access required")
    return user
