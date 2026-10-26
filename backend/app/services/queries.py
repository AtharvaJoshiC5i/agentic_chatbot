"""Read-side query helpers for REST APIs."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.tables import Delivery, Order, OrderItem, Product, Return


def list_returns(
    session: Session,
    *,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Return], int]:
    query = select(Return)
    if status:
        query = query.where(Return.return_status == status)
    count_query = select(func.count()).select_from(Return)
    if status:
        count_query = count_query.where(Return.return_status == status)
    total = session.execute(count_query).scalar_one()
    rows = session.execute(query.order_by(Return.request_date.desc()).limit(limit).offset(offset)).scalars().all()
    return list(rows), int(total)


def get_return_detail(session: Session, return_id: str) -> Return | None:
    return session.execute(select(Return).where(Return.return_id == return_id)).scalar_one_or_none()


def get_order_detail(session: Session, order_id: str) -> Order | None:
    return session.execute(
        select(Order).where(Order.order_id == order_id).options(selectinload(Order.items))
    ).scalar_one_or_none()


def get_product(session: Session, product_id: str) -> Product | None:
    return session.get(Product, product_id)
