from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Booking, Turf, User
from app.schemas import BookingCreate, BookingResponse

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("/", response_model=BookingResponse, status_code=201)
def create_booking(
	booking_data: BookingCreate,
	db: Annotated[Session, Depends(get_db)],
	current_user: Annotated[User, Depends(get_current_user)],
) -> Booking:
	if db.get(Turf, booking_data.turf_id) is None:
		raise HTTPException(status_code=404, detail="Turf not found")
	existing_booking = (
		db.query(Booking)
		.filter(
			Booking.turf_id == booking_data.turf_id,
			Booking.booking_date == booking_data.booking_date,
			Booking.slot_time == booking_data.slot_time,
			Booking.status == "confirmed",
		)
		.first()
	)
	if existing_booking:
		raise HTTPException(status_code=400, detail="Slot is already booked!")
	booking = Booking(user_id=current_user.id, **booking_data.model_dump())
	db.add(booking)
	db.commit()
	db.refresh(booking)
	return booking


@router.get("/me", response_model=list[BookingResponse])
def get_my_bookings(
	db: Annotated[Session, Depends(get_db)],
	current_user: Annotated[User, Depends(get_current_user)],
) -> list[Booking]:
	return (
		db.query(Booking)
		.filter(Booking.user_id == current_user.id, Booking.status == "confirmed")
		.order_by(Booking.booking_date, Booking.slot_time)
		.all()
	)


@router.patch("/{booking_id}/cancel", response_model=BookingResponse)
def cancel_booking(
	booking_id: int,
	db: Annotated[Session, Depends(get_db)],
	current_user: Annotated[User, Depends(get_current_user)],
) -> Booking:
	booking = db.get(Booking, booking_id)
	if booking is None:
		raise HTTPException(status_code=404, detail="Booking not found")
	if booking.user_id != current_user.id:
		raise HTTPException(status_code=403, detail="You can only cancel your own bookings")
	if booking.status == "cancelled":
		raise HTTPException(status_code=400, detail="Booking is already cancelled")
	booking.status = "cancelled"
	db.commit()
	db.refresh(booking)
	return booking
