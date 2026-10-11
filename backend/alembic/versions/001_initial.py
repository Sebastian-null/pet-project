"""initial shop schema

Revision ID: 001_initial
Revises:
Create Date: 2026-09-21
"""
import sqlalchemy as sa

from alembic import op

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    role = sa.Enum("ADMIN", "MANAGER", name="role")
    order_status = sa.Enum("NEW", "PAID", "PACKED", "SHIPPED", "DELIVERED", "CANCELLED", name="orderstatus")
    op.create_table("users", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("email", sa.String(255), nullable=False), sa.Column("password_hash", sa.String(255), nullable=False), sa.Column("role", role, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")), sa.UniqueConstraint("email"))
    op.create_index("ix_users_email", "users", ["email"])
    op.create_table("customers", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("email", sa.String(255), nullable=False), sa.Column("name", sa.String(160), nullable=False), sa.Column("phone", sa.String(32)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")), sa.UniqueConstraint("email"))
    op.create_index("ix_customers_email", "customers", ["email"])
    op.create_table("products", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("slug", sa.String(160), nullable=False), sa.Column("name", sa.String(255), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("material", sa.String(160), nullable=False), sa.Column("image_url", sa.String(500)), sa.Column("is_active", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")), sa.UniqueConstraint("slug"))
    op.create_index("ix_products_slug", "products", ["slug"])
    op.create_table("variants", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False), sa.Column("sku", sa.String(64), nullable=False), sa.Column("size", sa.String(16), nullable=False), sa.Column("color", sa.String(64), nullable=False), sa.Column("price", sa.Numeric(10, 2), nullable=False), sa.Column("stock", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")), sa.UniqueConstraint("sku"), sa.UniqueConstraint("product_id", "size", "color", name="uq_variant_option"))
    op.create_index("ix_variants_sku", "variants", ["sku"])
    op.create_table("orders", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False), sa.Column("status", order_status, nullable=False), sa.Column("total", sa.Numeric(10, 2), nullable=False), sa.Column("delivery_address", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")))
    op.create_table("order_items", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False), sa.Column("variant_id", sa.Integer(), sa.ForeignKey("variants.id"), nullable=False), sa.Column("title", sa.String(255), nullable=False), sa.Column("quantity", sa.Integer(), nullable=False), sa.Column("unit_price", sa.Numeric(10, 2), nullable=False))
def downgrade():
    op.drop_table("order_items"); op.drop_table("orders"); op.drop_index("ix_variants_sku", table_name="variants"); op.drop_table("variants"); op.drop_index("ix_products_slug", table_name="products"); op.drop_table("products"); op.drop_index("ix_customers_email", table_name="customers"); op.drop_table("customers"); op.drop_index("ix_users_email", table_name="users"); op.drop_table("users")
