from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
	__tablename__ = "users"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
	hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
	role: Mapped[str] = mapped_column(String(50), default="customer", nullable=False)

	bookings: Mapped[list["Booking"]] = relationship(
		back_populates="user", cascade="all, delete-orphan"
	)


class Turf(Base):
	__tablename__ = "turfs"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(255), nullable=False)
	location: Mapped[str] = mapped_column(String(255), nullable=False)
	hourly_rate: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

	bookings: Mapped[list["Booking"]] = relationship(
		back_populates="turf", cascade="all, delete-orphan"
	)


class Booking(Base):
	__tablename__ = "bookings"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
	turf_id: Mapped[int] = mapped_column(ForeignKey("turfs.id"), nullable=False, index=True)
	booking_date: Mapped[str] = mapped_column(String(10), nullable=False)
	slot_time: Mapped[str] = mapped_column(String(11), nullable=False)
	status: Mapped[str] = mapped_column(String(30), default="confirmed", nullable=False)

	user: Mapped[User] = relationship(back_populates="bookings")
	turf: Mapped[Turf] = relationship(back_populates="bookings")
