from datetime import date, datetime, time
from decimal import Decimal
import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class UserCreate(BaseModel):
	email: EmailStr
	password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: int
	email: EmailStr
	role: str


class Token(BaseModel):
	access_token: str
	token_type: str


class TurfCreate(BaseModel):
	name: str = Field(min_length=1, max_length=255)
	location: str = Field(min_length=1, max_length=255)
	turf_type: str = Field(default="football", min_length=1, max_length=100)
	open_time: str = Field(default="00:00")
	close_time: str = Field(default="23:59")
	hourly_rate: Decimal = Field(gt=0, max_digits=10, decimal_places=2)

	@field_validator("open_time", "close_time")
	@classmethod
	def validate_time(cls, value: str | None) -> str | None:
		if value is not None:
			try:
				datetime.strptime(value, "%H:%M")
			except ValueError as exc:
				raise ValueError("time must use HH:MM format") from exc
		return value

	@model_validator(mode="after")
	def validate_hours(self):
		open_time = datetime.strptime(self.open_time, "%H:%M").time()
		close_time = datetime.strptime(self.close_time, "%H:%M").time()
		if close_time <= open_time:
			raise ValueError("close_time must be after open_time")
		return self


class TurfResponse(TurfCreate):
	model_config = ConfigDict(from_attributes=True)

	id: int
	added_by_admin_id: int | None = None


class BookingCreate(BaseModel):
	turf_id: int = Field(gt=0)
	booking_date: str
	slot_time: str | None = None
	start_time: str | None = None
	end_time: str | None = None

	@field_validator("booking_date")
	@classmethod
	def validate_booking_date(cls, value: str) -> str:
		try:
			date.fromisoformat(value)
		except ValueError as exc:
			raise ValueError("booking_date must be a valid date in YYYY-MM-DD format") from exc
		return value

	@field_validator("start_time", "end_time")
	@classmethod
	def validate_time(cls, value: str | None) -> str | None:
		if value is not None and re.fullmatch(r"\d{2}:\d{2}", value) is None:
			raise ValueError("time must use HH:MM format")
		try:
			if value is not None:
				datetime.strptime(value, "%H:%M")
		except (ValueError, TypeError) as exc:
			raise ValueError("time must use HH:MM format") from exc
		return value

	@model_validator(mode="after")
	def normalize_times(self):
		if self.slot_time:
			if re.fullmatch(r"\d{2}:\d{2}-\d{2}:\d{2}", self.slot_time) is None:
				raise ValueError("slot_time must use HH:MM-HH:MM format")
			self.start_time, self.end_time = self.slot_time.split("-", maxsplit=1)
		elif not self.start_time or not self.end_time:
			raise ValueError("provide start_time and end_time, or slot_time")
		start = datetime.strptime(self.start_time, "%H:%M")
		end = datetime.strptime(self.end_time, "%H:%M")
		if end <= start:
			raise ValueError("end_time must be after start_time")
		self.slot_time = f"{self.start_time}-{self.end_time}"
		return self


class BookingResponse(BookingCreate):
	model_config = ConfigDict(from_attributes=True)

	id: int
	user_id: int
	status: str
	total_price: Decimal
	created_at: datetime


class WaitlistResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: int
	user_id: int
	turf_id: int
	booking_date: str
	start_time: str
	end_time: str
	status: str


class ReviewCreate(BaseModel):
	rating: int = Field(ge=1, le=5)
	comment: str | None = Field(default=None, max_length=1000)


class ReviewResponse(ReviewCreate):
	model_config = ConfigDict(from_attributes=True)

	id: int
	user_id: int
	turf_id: int
	created_at: datetime


class AnalyticsResponse(BaseModel):
	total_users: int
	total_turfs: int
	total_bookings: int
	confirmed_bookings: int
	cancelled_bookings: int
	total_revenue: Decimal
	average_rating: float | None
