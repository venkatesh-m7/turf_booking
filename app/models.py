from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
	__tablename__ = "users"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
	hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
	role: Mapped[str] = mapped_column(String(50), default="customer", nullable=False)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
	)

	bookings: Mapped[list["Booking"]] = relationship(
		back_populates="user", cascade="all, delete-orphan"
	)
	reviews: Mapped[list["Review"]] = relationship(
		back_populates="user", cascade="all, delete-orphan"
	)


class Turf(Base):
	__tablename__ = "turfs"

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	name: Mapped[str] = mapped_column(String(255), nullable=False)
	location: Mapped[str] = mapped_column(String(255), nullable=False)
	turf_type: Mapped[str] = mapped_column(String(100), default="football", nullable=False)
	open_time: Mapped[str] = mapped_column(String(5), default="00:00", nullable=False)
	close_time: Mapped[str] = mapped_column(String(5), default="23:59", nullable=False)
	hourly_rate: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
	added_by_admin_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
	)

	bookings: Mapped[list["Booking"]] = relationship(
		back_populates="turf", cascade="all, delete-orphan"
	)
	added_by_admin: Mapped[User | None] = relationship(foreign_keys=[added_by_admin_id])
	reviews: Mapped[list["Review"]] = relationship(
		back_populates="turf", cascade="all, delete-orphan"
	)


class Booking(Base):
	__tablename__ = "bookings"
	__table_args__ = (
		Index(
			"uq_confirmed_booking_slot",
			"turf_id",
			"booking_date",
			"start_time",
			"end_time",
			unique=True,
			postgresql_where=text("status = 'confirmed'"),
			sqlite_where=text("status = 'confirmed'"),
		),
	)

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
	turf_id: Mapped[int] = mapped_column(ForeignKey("turfs.id"), nullable=False, index=True)
	booking_date: Mapped[str] = mapped_column(String(10), nullable=False)
	slot_time: Mapped[str] = mapped_column(String(11), nullable=False)
	start_time: Mapped[str] = mapped_column(String(5), nullable=False)
	end_time: Mapped[str] = mapped_column(String(5), nullable=False)
	total_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
	status: Mapped[str] = mapped_column(String(30), default="confirmed", nullable=False)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
	)

	user: Mapped[User] = relationship(back_populates="bookings")
	turf: Mapped[Turf] = relationship(back_populates="bookings")


class Review(Base):
	__tablename__ = "reviews"
	__table_args__ = (Index("uq_user_turf_review", "user_id", "turf_id", unique=True),)

	id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
	user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
	turf_id: Mapped[int] = mapped_column(ForeignKey("turfs.id"), nullable=False, index=True)
	rating: Mapped[int] = mapped_column(Integer, nullable=False)
	comment: Mapped[str | None] = mapped_column(Text, nullable=True)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
	)

	user: Mapped[User] = relationship(back_populates="reviews")
	turf: Mapped[Turf] = relationship(back_populates="reviews")
