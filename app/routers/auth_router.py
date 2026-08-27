from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_password_hash, verify_password
from app.database import get_db
from app.models import User
from app.schemas import Token, UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Annotated[Session, Depends(get_db)]) -> User:
	email = str(user_data.email).lower()
	if db.query(User).filter(User.email == email).first():
		raise HTTPException(status_code=400, detail="Email already registered")
	user = User(email=email, hashed_password=get_password_hash(user_data.password))
	db.add(user)
	try:
		db.commit()
	except IntegrityError as exc:
		db.rollback()
		raise HTTPException(status_code=400, detail="Email already registered") from exc
	db.refresh(user)
	return user


@router.post("/login", response_model=Token)
def login(
	form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
	db: Annotated[Session, Depends(get_db)],
) -> Token:
	user = db.query(User).filter(User.email == form_data.username.lower()).first()
	if user is None or not verify_password(form_data.password, user.hashed_password):
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Incorrect email or password",
			headers={"WWW-Authenticate": "Bearer"},
		)
	return Token(access_token=create_access_token(user.id), token_type="bearer")
