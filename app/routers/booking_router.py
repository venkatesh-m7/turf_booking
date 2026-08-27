from datetime import datetime, timedelta
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models import Booking, Turf, User, WaitlistEntry
from app.schemas import BookingCreate, BookingResponse, WaitlistResponse

router = APIRouter(prefix="/bookings", tags=["bookings"])


def parse_time(value: str) -> datetime:
	return datetime.strptime(value, "%H:%M")


def calculate_price(turf: Turf, start_time: str, end_time: str) -> Decimal:
	duration_hours = Decimal((parse_time(end_time) - parse_time(start_time)).seconds) / Decimal(3600)
	return (Decimal(str(turf.hourly_rate)) * duration_hours).quantize(Decimal("0.01"))


@router.post("/", response_model=BookingResponse, status_code=201)
def create_booking(
	booking_data: BookingCreate,
	db: Annotated[Session, Depends(get_db)],
	current_user: Annotated[User, Depends(get_current_user)],
) -> Booking:
	turf = db.get(Turf, booking_data.turf_id)
	if turf is None:
		raise HTTPException(status_code=404, detail="Turf not found")
	start_time = booking_data.start_time
	end_time = booking_data.end_time
	assert start_time is not None and end_time is not None
	if start_time < turf.open_time or end_time > turf.close_time:
		raise HTTPException(status_code=400, detail="Booking is outside turf operating hours")
	existing_booking = (
		db.query(Booking)
		.filter(
			Booking.turf_id == booking_data.turf_id,
			Booking.booking_date == booking_data.booking_date,
			Booking.start_time == start_time,
			Booking.end_time == end_time,
			Booking.status == "confirmed",
		)
		.first()
	)
	if existing_booking:
		raise HTTPException(status_code=400, detail="Slot is already booked!")
	booking = Booking(
		user_id=current_user.id,
		turf_id=booking_data.turf_id,
		booking_date=booking_data.booking_date,
		slot_time=booking_data.slot_time,
		start_time=start_time,
		end_time=end_time,
		total_price=calculate_price(turf, start_time, end_time),
	)
	db.add(booking)
	try:
		db.commit()
	except IntegrityError as exc:
		db.rollback()
		raise HTTPException(status_code=400, detail="Slot is already booked!") from exc
	db.refresh(booking)
	return booking


@router.post("/waitlist", response_model=WaitlistResponse, status_code=201)
def join_waitlist(
	booking_data: BookingCreate,
	db: Annotated[Session, Depends(get_db)],
	current_user: Annotated[User, Depends(get_current_user)],
) -> WaitlistEntry:
	turf = db.get(Turf, booking_data.turf_id)
	if turf is None:
		raise HTTPException(status_code=404, detail="Turf not found")
	start_time = booking_data.start_time
	end_time = booking_data.end_time
	assert start_time is not None and end_time is not None
	if not db.query(Booking).filter(
		Booking.turf_id == turf.id,
		Booking.booking_date == booking_data.booking_date,
		Booking.start_time == start_time,
		Booking.end_time == end_time,
		Booking.status == "confirmed",
	).first():
		raise HTTPException(status_code=400, detail="This slot is available; book it directly")
	entry = WaitlistEntry(
		user_id=current_user.id,
		turf_id=turf.id,
		booking_date=booking_data.booking_date,
		start_time=start_time,
		end_time=end_time,
	)
	db.add(entry)
	try:
		db.commit()
	except IntegrityError as exc:
		db.rollback()
		raise HTTPException(status_code=400, detail="You are already on this waitlist") from exc
	db.refresh(entry)
	return entry


@router.get("/waitlist/me", response_model=list[WaitlistResponse])
def get_my_waitlist(
	db: Annotated[Session, Depends(get_db)],
	current_user: Annotated[User, Depends(get_current_user)],
) -> list[WaitlistEntry]:
	return db.query(WaitlistEntry).filter(
		WaitlistEntry.user_id == current_user.id,
		WaitlistEntry.status == "waiting",
	).order_by(WaitlistEntry.created_at).all()


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
	booking_start = datetime.strptime(f"{booking.booking_date} {booking.start_time}", "%Y-%m-%d %H:%M")
	if booking_start - datetime.now() < timedelta(hours=settings.CANCELLATION_CUTOFF_HOURS):
		raise HTTPException(status_code=400, detail="Bookings cannot be cancelled within the cutoff window")
	booking.status = "cancelled"
	waitlist_entry = db.query(WaitlistEntry).filter(
		WaitlistEntry.turf_id == booking.turf_id,
		WaitlistEntry.booking_date == booking.booking_date,
		WaitlistEntry.start_time == booking.start_time,
		WaitlistEntry.end_time == booking.end_time,
		WaitlistEntry.status == "waiting",
	).order_by(WaitlistEntry.created_at).first()
	if waitlist_entry:
		db.add(Booking(
			user_id=waitlist_entry.user_id,
			turf_id=booking.turf_id,
			booking_date=booking.booking_date,
			slot_time=booking.slot_time,
			start_time=booking.start_time,
			end_time=booking.end_time,
			total_price=booking.total_price,
		))
		waitlist_entry.status = "fulfilled"
	db.commit()
	db.refresh(booking)
	return booking
