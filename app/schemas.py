from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


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
	hourly_rate: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class TurfResponse(TurfCreate):
	model_config = ConfigDict(from_attributes=True)

	id: int


class BookingCreate(BaseModel):
	turf_id: int = Field(gt=0)
	booking_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
	slot_time: str = Field(pattern=r"^\d{2}:\d{2}-\d{2}:\d{2}$")


class BookingResponse(BookingCreate):
	model_config = ConfigDict(from_attributes=True)

	id: int
	user_id: int
	status: str
