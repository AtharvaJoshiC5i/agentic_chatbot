"""Product read APIs."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.api import ProductSummary
from app.security.deps import CurrentUser, get_current_user
from app.services.queries import get_product

router = APIRouter(prefix="/products", dependencies=[Depends(get_current_user)])


@router.get("/{product_id}", response_model=ProductSummary)
def get_product_by_id(
    product_id: str,
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
) -> ProductSummary:
    product = get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return ProductSummary.model_validate(product)
