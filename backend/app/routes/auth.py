"""Authentication routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.tables import User
from app.schemas.api import LoginRequest, TokenResponse
from app.security.passwords import verify_password
from app.security.tokens import create_access_token

router = APIRouter(prefix="/auth")


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.execute(select(User).where(User.username == payload.username)).scalar_one_or_none()
    if user is None or not user.active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(user.username, user.role)
    return TokenResponse(access_token=token, role=user.role, username=user.username)
