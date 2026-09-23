from sqlalchemy import select
from .db import SessionLocal
from .models import Customer, Product, Role, User, Variant
from .security import password_hash

def run():
    with SessionLocal() as db:
        if not db.scalar(select(User).where(User.email == "admin@briefs.local")):
            db.add(User(email="admin@briefs.local", password_hash=password_hash("change-me-now"), role=Role.ADMIN))
        if not db.scalar(select(Customer).where(Customer.email == "test@briefs.local")):
            db.add(Customer(email="test@briefs.local", name="Test Customer", password_hash=password_hash("BriefsTest2026!")))
        if not db.scalar(select(Product).limit(1)):
            product = Product(slug="everyday-cotton", name="Everyday Cotton", description="Мягкие брифы на каждый день: дышащий хлопок и комфортная посадка.", material="95% хлопок, 5% эластан", image_url="https://images.unsplash.com/photo-1617127365659-c47fa864d8bc?auto=format&fit=crop&w=900&q=80")
            product.variants = [Variant(sku=f"EDC-BLK-{size}", size=size, color="Чорний", price=590, stock=12) for size in ["S", "M", "L", "XL", "XXL"]] + [Variant(sku="EDC-SND-M", size="M", color="Пісочний", price=590, stock=3)]
            product2 = Product(slug="soft-modal", name="Soft Modal", description="Гладкая премиальная модель из модала — для дней, когда хочется максимум мягкости.", material="92% модал, 8% эластан", image_url="https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?auto=format&fit=crop&w=900&q=80")
            product2.variants = [Variant(sku=f"SMD-BLU-{size}", size=size, color="Синій", price=790, stock=10) for size in ["S", "M", "L", "XL", "XXL"]]
            db.add_all([product, product2])
        db.commit()
if __name__ == "__main__": run()
