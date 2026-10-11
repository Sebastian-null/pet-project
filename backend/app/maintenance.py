import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from . import payments
from .db import SessionLocal
from .models import EmailVerification, Order, OrderStatus

log = logging.getLogger(__name__)
# Stripe expires a checkout session after 30 minutes; the sweep is the safety net
# for sessions whose expiry webhook never arrived, so it waits a little longer.
ABANDONED_AFTER = timedelta(minutes=35)
SWEEP_INTERVAL_SECONDS = 10 * 60


def sweep(db: Session) -> tuple[int, int]:
    """Give stock back from abandoned orders and drop verification codes nobody used."""
    now = datetime.now(UTC)
    abandoned = db.scalars(
        select(Order).where(Order.status == OrderStatus.NEW, Order.created_at < now - ABANDONED_AFTER).options(selectinload(Order.items))
    ).all()
    for order in abandoned:
        payments.release(db, order)
    expired_codes = db.query(EmailVerification).filter(EmailVerification.expires_at < now).delete()
    db.commit()
    return len(abandoned), expired_codes


async def sweep_periodically() -> None:
    while True:
        await asyncio.sleep(SWEEP_INTERVAL_SECONDS)
        try:
            with SessionLocal() as db:
                cancelled, codes = sweep(db)
            if cancelled or codes:
                log.info("Maintenance: cancelled %s abandoned orders, removed %s expired codes", cancelled, codes)
        except Exception:
            log.exception("Maintenance sweep failed")
