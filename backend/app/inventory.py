from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Order, OrderStatus, Variant


def return_stock(db: Session, order: Order) -> None:
    """Put the units reserved by an order back on the shelf."""
    for item in order.items:
        variant = db.scalar(select(Variant).where(Variant.id == item.variant_id).with_for_update())
        if variant:
            variant.stock += item.quantity


def cancel(db: Session, order: Order) -> bool:
    """Cancel an order and return its stock. Cancelling twice is a no-op."""
    if order.status == OrderStatus.CANCELLED:
        return False
    return_stock(db, order)
    order.status = OrderStatus.CANCELLED
    db.commit()
    return True
