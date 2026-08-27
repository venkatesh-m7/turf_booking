from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Booking, Review, Turf, User
from app.schemas import AnalyticsResponse

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
	if user.role != "admin":
		raise HTTPException(status_code=403, detail="Admin access required")
	return user


@router.get("/analytics", response_model=AnalyticsResponse)
def analytics(
	db: Annotated[Session, Depends(get_db)],
	_: Annotated[User, Depends(require_admin)],
) -> AnalyticsResponse:
	total_revenue = db.query(func.coalesce(func.sum(Booking.total_price), 0)).filter(
		Booking.status == "confirmed"
	).scalar()
	average_rating = db.query(func.avg(Review.rating)).scalar()
	return AnalyticsResponse(
		total_users=db.query(User).count(),
		total_turfs=db.query(Turf).count(),
		total_bookings=db.query(Booking).count(),
		confirmed_bookings=db.query(Booking).filter(Booking.status == "confirmed").count(),
		cancelled_bookings=db.query(Booking).filter(Booking.status == "cancelled").count(),
		total_revenue=Decimal(str(total_revenue or 0)),
		average_rating=float(average_rating) if average_rating is not None else None,
	)


@router.get("/bookings", response_model=list[dict])
def list_all_bookings(
	db: Annotated[Session, Depends(get_db)],
	_: Annotated[User, Depends(require_admin)],
) -> list[dict]:
	bookings = db.query(Booking).order_by(Booking.created_at.desc()).all()
	return [
		{
			"id": booking.id,
			"user_id": booking.user_id,
			"turf_id": booking.turf_id,
			"booking_date": booking.booking_date,
			"start_time": booking.start_time,
			"end_time": booking.end_time,
			"total_price": booking.total_price,
			"status": booking.status,
		}
		for booking in bookings
	]