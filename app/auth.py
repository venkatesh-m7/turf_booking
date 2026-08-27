from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
	return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
	return pwd_context.hash(password)


def create_access_token(subject: str | int, expires_delta: timedelta | None = None) -> str:
	expires = datetime.now(timezone.utc) + (
		expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
	)
	return jwt.encode(
		{"sub": str(subject), "exp": expires}, settings.SECRET_KEY, algorithm=settings.ALGORITHM
	)


def get_current_user(
	token: Annotated[str, Depends(oauth2_scheme)],
	db: Annotated[Session, Depends(get_db)],
) -> User:
	credentials_exception = HTTPException(
		status_code=status.HTTP_401_UNAUTHORIZED,
		detail="Could not validate credentials",
		headers={"WWW-Authenticate": "Bearer"},
	)
	try:
		payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
		subject = payload.get("sub")
		if subject is None:
			raise credentials_exception
		user = db.get(User, int(subject))
	except (JWTError, ValueError, TypeError):
		raise credentials_exception
	if user is None:
		raise credentials_exception
	return user
