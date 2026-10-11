"""split the catalogue into women's and men's ranges

Revision ID: 006_product_gender_and_category
Revises: 005_customer_profile
Create Date: 2026-09-25
"""
import sqlalchemy as sa

from alembic import op

revision = "006_product_gender_and_category"
down_revision = "005_customer_profile"
branch_labels = None
depends_on = None

def upgrade():
    gender = sa.Enum("WOMEN", "MEN", name="gender")
    gender.create(op.get_bind(), checkfirst=True)
    op.add_column("products", sa.Column("gender", gender, nullable=False, server_default="WOMEN"))
    op.add_column("products", sa.Column("category", sa.String(64), nullable=False, server_default="briefs"))
    op.execute("update products set gender = 'MEN' where slug = 'everyday-cotton'")
    op.execute("update products set category = 'slip' where slug = 'soft-modal'")

def downgrade():
    op.drop_column("products", "category")
    op.drop_column("products", "gender")
    sa.Enum(name="gender").drop(op.get_bind(), checkfirst=True)
