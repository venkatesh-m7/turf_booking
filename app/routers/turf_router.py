from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Booking, Review, Turf, User
from app.schemas import ReviewCreate, ReviewResponse, TurfCreate, TurfResponse

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
	turf.added_by_admin_id = current_user.id
	db.add(turf)
	try:
		db.commit()
	except IntegrityError as exc:
		db.rollback()
		raise HTTPException(status_code=400, detail="Could not create turf") from exc
	db.refresh(turf)
	return turf


@router.patch("/{turf_id}", response_model=TurfResponse)
def update_turf(
	turf_id: int,
	turf_data: TurfCreate,
	db: Annotated[Session, Depends(get_db)],
	current_user: Annotated[User, Depends(get_current_user)],
) -> Turf:
	if current_user.role != "admin":
		raise HTTPException(status_code=403, detail="Admin access required")
	turf = db.get(Turf, turf_id)
	if turf is None:
		raise HTTPException(status_code=404, detail="Turf not found")
	for field, value in turf_data.model_dump().items():
		setattr(turf, field, value)
	db.commit()
	db.refresh(turf)
	return turf


@router.delete("/{turf_id}", status_code=204)
def delete_turf(
	turf_id: int,
	db: Annotated[Session, Depends(get_db)],
	current_user: Annotated[User, Depends(get_current_user)],
) -> None:
	if current_user.role != "admin":
		raise HTTPException(status_code=403, detail="Admin access required")
	turf = db.get(Turf, turf_id)
	if turf is None:
		raise HTTPException(status_code=404, detail="Turf not found")
	db.delete(turf)
	db.commit()


@router.post("/{turf_id}/reviews", response_model=ReviewResponse, status_code=201)
def create_review(
	turf_id: int,
	review_data: ReviewCreate,
	db: Annotated[Session, Depends(get_db)],
	current_user: Annotated[User, Depends(get_current_user)],
) -> Review:
	if db.get(Turf, turf_id) is None:
		raise HTTPException(status_code=404, detail="Turf not found")
	if not db.query(Booking).filter(
		Booking.turf_id == turf_id,
		Booking.user_id == current_user.id,
		Booking.status.in_(["confirmed", "cancelled"]),
	).first():
		raise HTTPException(status_code=403, detail="You can review a turf only after booking it")
	review = Review(user_id=current_user.id, turf_id=turf_id, **review_data.model_dump())
	db.add(review)
	try:
		db.commit()
	except IntegrityError as exc:
		db.rollback()
		raise HTTPException(status_code=400, detail="You have already reviewed this turf") from exc
	db.refresh(review)
	return review


@router.get("/{turf_id}/reviews", response_model=list[ReviewResponse])
def list_reviews(turf_id: int, db: Annotated[Session, Depends(get_db)]) -> list[Review]:
	if db.get(Turf, turf_id) is None:
		raise HTTPException(status_code=404, detail="Turf not found")
	return db.query(Review).filter(Review.turf_id == turf_id).order_by(Review.created_at.desc()).all()
