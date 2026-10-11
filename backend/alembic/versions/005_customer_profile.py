"""customer profile fields

Revision ID: 005_customer_profile
Revises: 004_stripe_payments
Create Date: 2026-09-24
"""
import sqlalchemy as sa

from alembic import op

revision = "005_customer_profile"
down_revision = "004_stripe_payments"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("customers", sa.Column("birth_date", sa.Date(), nullable=True))
    op.add_column("customers", sa.Column("avatar_url", sa.String(500), nullable=True))

def downgrade():
    op.drop_column("customers", "avatar_url")
    op.drop_column("customers", "birth_date")
