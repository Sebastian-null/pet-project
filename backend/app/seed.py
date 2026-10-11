from sqlalchemy import select

from .db import SessionLocal
from .models import Customer, Gender, Product, Role, User, Variant
from .security import password_hash

BRIEF_SIZES = ["S", "M", "L", "XL"]
BRA_SIZES = ["70B", "75B", "80B", "80C"]

CATALOGUE = [
    {
        "slug": "everyday-cotton", "name": "Everyday Cotton", "sku": "EDC", "gender": Gender.MEN, "category": "briefs",
        "description": "М’які брифи на щодень: дихаюча бавовна та комфортна посадка.", "material": "95% бавовна, 5% еластан",
        "price": 590, "sizes": [*BRIEF_SIZES, "XXL"], "colors": {"black": "BLK", "sand": "SND"}, "stock": 12,
    },
    {
        "slug": "classic-boxer", "name": "Classic Boxer", "sku": "CBX", "gender": Gender.MEN, "category": "boxers",
        "description": "Боксери вільного крою з пласкими швами — не тиснуть і не задираються.", "material": "95% бавовна, 5% еластан",
        "price": 520, "sizes": [*BRIEF_SIZES, "XXL"], "colors": {"black": "BLK", "navy": "NVY"}, "stock": 11,
    },
    {
        "slug": "sport-trunk", "name": "Sport Trunk", "sku": "STR", "gender": Gender.MEN, "category": "trunks",
        "description": "Короткі транки для тренувань: тканина відводить вологу й швидко сохне.", "material": "90% поліамід, 10% еластан",
        "price": 480, "sizes": BRIEF_SIZES, "colors": {"black": "BLK", "grey": "GRY"}, "stock": 10,
    },
    {
        "slug": "bamboo-brief", "name": "Bamboo Brief", "sku": "BMB", "gender": Gender.MEN, "category": "briefs",
        "description": "Брифи з бамбукового волокна — природно антибактеріальні та дуже легкі.", "material": "70% бамбук, 25% бавовна, 5% еластан",
        "price": 440, "sizes": BRIEF_SIZES, "colors": {"black": "BLK", "khaki": "KHK"}, "stock": 8,
    },
    {
        "slug": "soft-modal", "name": "Soft Modal", "sku": "SMD", "gender": Gender.WOMEN, "category": "slip",
        "description": "Гладка преміальна модель із модалу — коли хочеться максимальної м’якості.", "material": "92% модал, 8% еластан",
        "price": 790, "sizes": [*BRIEF_SIZES, "XXL"], "colors": {"blue": "BLU"}, "stock": 10,
    },
    {
        "slug": "cotton-slip", "name": "Cotton Slip", "sku": "CSL", "gender": Gender.WOMEN, "category": "slip",
        "description": "Сліпи з органічної бавовни з широкою м’якою резинкою, що не лишає слідів.", "material": "95% бавовна, 5% еластан",
        "price": 390, "sizes": BRIEF_SIZES, "colors": {"black": "BLK", "white": "WHT"}, "stock": 14,
    },
    {
        "slug": "high-waist-brief", "name": "High Waist Brief", "sku": "HWB", "gender": Gender.WOMEN, "category": "briefs",
        "description": "Трусики з високою посадкою, що м’яко тримають силует під сукнею.", "material": "92% модал, 8% еластан",
        "price": 450, "sizes": BRIEF_SIZES, "colors": {"black": "BLK", "beige": "BGE"}, "stock": 9,
    },
    {
        "slug": "lace-thong", "name": "Lace Thong", "sku": "LTH", "gender": Gender.WOMEN, "category": "thong",
        "description": "Стрінги з еластичного мережива — непомітні навіть під тонкою тканиною.", "material": "85% поліамід, 15% еластан",
        "price": 350, "sizes": ["S", "M", "L"], "colors": {"black": "BLK", "powder": "PWD"}, "stock": 12,
    },
    {
        "slug": "lace-bralette", "name": "Lace Bralette", "sku": "LBR", "gender": Gender.WOMEN, "category": "bralette",
        "description": "Невагомий бралет із французького мережива, без кісточок і застібок.", "material": "82% поліамід, 18% еластан",
        "price": 690, "sizes": ["XS", "S", "M", "L"], "colors": {"black": "BLK", "powder": "PWD"}, "stock": 8,
    },
    {
        "slug": "push-up-classic", "name": "Push-Up Classic", "sku": "PUC", "gender": Gender.WOMEN, "category": "bra",
        "description": "Класичний push-up із гладкою чашкою — тримає форму й не видно під одягом.", "material": "75% поліамід, 25% еластан",
        "price": 890, "sizes": BRA_SIZES, "colors": {"black": "BLK", "beige": "BGE"}, "stock": 6,
    },
    {
        "slug": "active-sport-bra", "name": "Active Sport Bra", "sku": "ASB", "gender": Gender.WOMEN, "category": "bra",
        "description": "Спортивний топ середньої підтримки з дихаючого трикотажу.", "material": "88% поліестер, 12% еластан",
        "price": 790, "sizes": ["XS", "S", "M", "L"], "colors": {"black": "BLK", "grey": "GRY"}, "stock": 10,
    },
]


def run():
    with SessionLocal() as db:
        if not db.scalar(select(User).where(User.email == "admin@briefs.store")):
            db.add(User(email="admin@briefs.store", password_hash=password_hash("change-me-now"), role=Role.ADMIN))
        if not db.scalar(select(User).where(User.email == "manager@briefs.store")):
            db.add(User(email="manager@briefs.store", password_hash=password_hash("change-me-now"), role=Role.MANAGER))
        if not db.scalar(select(Customer).where(Customer.email == "test@briefs.store")):
            db.add(Customer(email="test@briefs.store", name="Test Customer", password_hash=password_hash("BriefsTest2026!")))
        for item in CATALOGUE:
            if db.scalar(select(Product).where(Product.slug == item["slug"])):
                continue
            product = Product(
                slug=item["slug"], name=item["name"], description=item["description"], material=item["material"],
                gender=item["gender"], category=item["category"], image_url=None,
            )
            product.variants = [
                Variant(sku=f"{item['sku']}-{code}-{size}", size=size, color=color, price=item["price"], stock=item["stock"])
                for color, code in item["colors"].items()
                for size in item["sizes"]
            ]
            db.add(product)
        db.commit()


if __name__ == "__main__":
    run()
