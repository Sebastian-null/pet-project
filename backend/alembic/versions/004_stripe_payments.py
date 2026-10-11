"""stripe payment references on orders

Revision ID: 004_stripe_payments
Revises: 003_email_verification
Create Date: 2026-09-24
"""
import sqlalchemy as sa

from alembic import op

revision = "004_stripe_payments"
down_revision = "003_email_verification"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("orders", sa.Column("payment_session_id", sa.String(255), nullable=True))
    op.add_column("orders", sa.Column("payment_intent_id", sa.String(255), nullable=True))
    op.add_column("orders", sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_orders_payment_session_id", "orders", ["payment_session_id"])

def downgrade():
    op.drop_index("ix_orders_payment_session_id", table_name="orders")
    op.drop_column("orders", "paid_at")
    op.drop_column("orders", "payment_intent_id")
    op.drop_column("orders", "payment_session_id")
