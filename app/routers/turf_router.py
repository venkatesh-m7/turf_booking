from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Turf, User
from app.schemas import TurfCreate, TurfResponse

router = APIRouter(prefix="/turfs", tags=["turfs"])


@router.get("", response_model=list[TurfResponse])
def list_turfs(db: Annotated[Session, Depends(get_db)]) -> list[Turf]:
	return db.query(Turf).order_by(Turf.id).all()


@router.post("", response_model=TurfResponse, status_code=201)
def create_turf(
	turf_data: TurfCreate,
	db: Annotated[Session, Depends(get_db)],
	current_user: Annotated[User, Depends(get_current_user)],
) -> Turf:
	if current_user.role != "admin":
		raise HTTPException(status_code=403, detail="Admin access required")
	turf = Turf(**turf_data.model_dump())
	db.add(turf)
	db.commit()
	db.refresh(turf)
	return turf
