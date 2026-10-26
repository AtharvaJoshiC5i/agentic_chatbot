"""Order read APIs."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.tables import OrderItem
from app.schemas.api import OrderDetail, OrderItemSummary
from app.security.deps import CurrentUser, get_current_user
from app.services.queries import get_order_detail

router = APIRouter(prefix="/orders", dependencies=[Depends(get_current_user)])


@router.get("/{order_id}", response_model=OrderDetail)
def get_order(order_id: str, db: Session = Depends(get_db), _user: CurrentUser = Depends(get_current_user)) -> OrderDetail:
    order = get_order_detail(db, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    items = db.execute(select(OrderItem).where(OrderItem.order_id == order.order_id)).scalars().all()
    return OrderDetail(
        order_id=order.order_id,
        customer_id=order.customer_id,
        order_date=order.order_date,
        total_amount_paise=order.total_amount,
        order_status=order.order_status,
        items=[OrderItemSummary.model_validate(item) for item in items],
    )
