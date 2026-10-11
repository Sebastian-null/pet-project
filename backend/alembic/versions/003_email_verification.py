"""email verification codes

Revision ID: 003_email_verification
Revises: 002_customer_accounts_and_sizes
Create Date: 2026-09-21
"""
import sqlalchemy as sa

from alembic import op

revision = "003_email_verification"
down_revision = "002_customer_accounts_and_sizes"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("email_verifications", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("email", sa.String(255), nullable=False), sa.Column("name", sa.String(160), nullable=False), sa.Column("password_hash", sa.String(255), nullable=False), sa.Column("code_hash", sa.String(64), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")))
    op.create_index("ix_email_verifications_email", "email_verifications", ["email"])
def downgrade():
    op.drop_index("ix_email_verifications_email", table_name="email_verifications")
    op.drop_table("email_verifications")
