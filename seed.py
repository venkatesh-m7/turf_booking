from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.auth import get_password_hash
from app.database import Base, SessionLocal, engine
from app.models import Booking, Review, Turf, User


USERS = [
    {
        "email": "admin@gmail.com",
        "password": "admin123",
        "role": "admin",
    },
    {
        "email": "customer1@gmail.com",
        "password": "customer1123",
        "role": "customer",
    },
]

TURFS = [
    {
        "name": "Central Football Turf",
        "location": "Downtown",
        "turf_type": "football",
        "open_time": "08:00",
        "close_time": "22:00",
        "hourly_rate": Decimal("150.00"),
    },
    {
        "name": "Arena Cricket Ground",
        "location": "North District",
        "turf_type": "cricket",
        "open_time": "06:00",
        "close_time": "23:00",
        "hourly_rate": Decimal("200.00"),
    },
    {
        "name": "City Badminton Court",
        "location": "West End",
        "turf_type": "badminton",
        "open_time": "07:00",
        "close_time": "21:00",
        "hourly_rate": Decimal("100.00"),
    },
]


def get_or_create_user(db: Session, user_data: dict) -> User:
    user = db.query(User).filter(User.email == user_data["email"]).first()
    if user is None:
        user = User(
            email=user_data["email"],
            hashed_password=get_password_hash(user_data["password"]),
            role=user_data["role"],
        )
        db.add(user)
        db.flush()
    return user


def get_or_create_turf(db: Session, turf_data: dict, admin_id: int) -> Turf:
    turf = db.query(Turf).filter(Turf.name == turf_data["name"]).first()
    if turf is None:
        turf = Turf(**turf_data, added_by_admin_id=admin_id)
        db.add(turf)
        db.flush()
    return turf


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        users = {user_data["email"]: get_or_create_user(db, user_data) for user_data in USERS}
        admin = users["admin@gmail.com"]
        customer = users["customer1@gmail.com"]
        turfs = [get_or_create_turf(db, turf_data, admin.id) for turf_data in TURFS]

        booking = (
            db.query(Booking)
            .filter(
                Booking.turf_id == turfs[0].id,
                Booking.booking_date == "2099-06-15",
                Booking.start_time == "18:00",
                Booking.end_time == "19:00",
            )
            .first()
        )
        if booking is None:
            booking = Booking(
                user_id=customer.id,
                turf_id=turfs[0].id,
                booking_date="2099-06-15",
                slot_time="18:00-19:00",
                start_time="18:00",
                end_time="19:00",
                total_price=Decimal("150.00"),
                status="confirmed",
            )
            db.add(booking)
            db.flush()

        review = db.query(Review).filter(
            Review.user_id == customer.id,
            Review.turf_id == turfs[0].id,
        ).first()
        if review is None:
            db.add(Review(
                user_id=customer.id,
                turf_id=turfs[0].id,
                rating=5,
                comment="Great facilities and easy booking.",
            ))

        db.commit()
        print("Seed data created or already present.")
        print("Admin login: admin@gmail.com / admin123")
        print("Customer login: customer1@gmail.com / customer1123")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
