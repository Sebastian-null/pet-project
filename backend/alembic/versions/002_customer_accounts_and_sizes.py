"""customer password accounts and complete size grid

Revision ID: 002_customer_accounts_and_sizes
Revises: 001_initial
Create Date: 2026-09-21
"""
import sqlalchemy as sa

from alembic import op

revision = "002_customer_accounts_and_sizes"
down_revision = "001_initial"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("customers", sa.Column("password_hash", sa.String(255), nullable=True))
    op.execute("UPDATE variants SET color = CASE color WHEN 'Чёрный' THEN 'Чорний' WHEN 'Песочный' THEN 'Пісочний' WHEN 'Синий' THEN 'Синій' ELSE color END")
    # Existing demo models receive a selectable S–XXL grid without changing existing SKUs.
    op.execute("INSERT INTO variants (product_id, sku, size, color, price, stock) SELECT 1, 'EDC-BLK-' || s, s, 'Чорний', 590, 10 FROM unnest(ARRAY['S','XL','XXL']) s")
    op.execute("INSERT INTO variants (product_id, sku, size, color, price, stock) SELECT 2, 'SMD-BLU-' || s, s, 'Синій', 790, 10 FROM unnest(ARRAY['S','XL','XXL']) s")
def downgrade():
    op.execute("DELETE FROM variants WHERE sku IN ('EDC-BLK-S','EDC-BLK-XL','EDC-BLK-XXL','SMD-BLU-S','SMD-BLU-XL','SMD-BLU-XXL')")
    op.drop_column("customers", "password_hash")
