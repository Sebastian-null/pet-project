"""store variant colours as stable codes instead of Ukrainian display names

Revision ID: 007_colour_codes
Revises: 006_product_gender_and_category
Create Date: 2026-10-11

The storefront is bilingual, but a colour was stored the way a shopper reads it
in Ukrainian, so the English pages showed "Чорний". Colours now follow the same
rule as categories: a code in the database, the display name in the storefront
dictionaries. Order items keep the text they were written with — they are a
snapshot of what was bought, not a live reference to the catalogue.
"""
import sqlalchemy as sa

from alembic import op

revision = "007_colour_codes"
down_revision = "006_product_gender_and_category"
branch_labels = None
depends_on = None

# "Синій" covered two different colours, told apart by the SKU.
CODES = {
    "Чорний": "black",
    "Пісочний": "sand",
    "Сірий": "grey",
    "Хакі": "khaki",
    "Білий": "white",
    "Бежевий": "beige",
    "Пудровий": "powder",
}

def upgrade():
    connection = op.get_bind()
    for ukrainian, code in CODES.items():
        connection.execute(sa.text("update variants set color = :code where color = :ukrainian"), {"code": code, "ukrainian": ukrainian})
    connection.execute(sa.text("update variants set color = 'navy' where color = 'Синій' and sku like '%-NVY-%'"))
    connection.execute(sa.text("update variants set color = 'blue' where color = 'Синій'"))

def downgrade():
    connection = op.get_bind()
    for ukrainian, code in CODES.items():
        connection.execute(sa.text("update variants set color = :ukrainian where color = :code"), {"code": code, "ukrainian": ukrainian})
    connection.execute(sa.text("update variants set color = 'Синій' where color in ('navy', 'blue')"))
