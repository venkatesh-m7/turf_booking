import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth import get_password_hash
from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import Turf, User

TEST_DATABASE_URL = "sqlite:///./test.db"
test_engine = create_engine(
	TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
	db = TestingSessionLocal()
	try:
		yield db
	finally:
		db.close()


@pytest.fixture(autouse=True)
def test_database(monkeypatch):
	import app.main as main_module

	monkeypatch.setattr(main_module, "engine", test_engine)
	Base.metadata.create_all(bind=test_engine)
	app.dependency_overrides[get_db] = override_get_db
	yield
	app.dependency_overrides.clear()
	Base.metadata.drop_all(bind=test_engine)


def test_root_endpoint():
	with TestClient(app) as client:
		response = client.get("/")
	assert response.status_code == 200
	assert response.json() == {"message": "Turf Booking API is running"}


def test_user_registration():
	with TestClient(app) as client:
		response = client.post(
			"/auth/register",
			json={"email": "player@example.com", "password": "strongpassword"},
		)
	assert response.status_code == 201
	assert response.json()["email"] == "player@example.com"
	assert response.json()["role"] == "customer"


def register_user(client: TestClient, email: str) -> dict:
	response = client.post(
		"/auth/register",
		json={"email": email, "password": "strongpassword"},
	)
	assert response.status_code == 201
	return response.json()


def login_user(client: TestClient, email: str) -> str:
	response = client.post(
		"/auth/login",
		data={"username": email, "password": "strongpassword"},
	)
	assert response.status_code == 200
	return response.json()["access_token"]


def seed_turf() -> Turf:
	db = TestingSessionLocal()
	try:
		turf = Turf(name="Central Turf", location="Downtown", hourly_rate=150)
		db.add(turf)
		db.commit()
		db.refresh(turf)
		return turf
	finally:
		db.close()


def make_admin(email: str) -> None:
	db = TestingSessionLocal()
	try:
		user = db.query(User).filter(User.email == email).one()
		user.role = "admin"
		db.commit()
	finally:
		db.close()


def test_login_returns_jwt_token():
	with TestClient(app) as client:
		register_user(client, "login@example.com")
		token = login_user(client, "login@example.com")

	payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
	assert payload["sub"] == "1"
	assert payload["exp"] > 0


def test_public_turf_listing():
	seed_turf()

	with TestClient(app) as client:
		response = client.get("/turfs")

	assert response.status_code == 200
	listing = response.json()
	assert len(listing) == 1
	assert listing[0]["name"] == "Central Turf"
	assert listing[0]["hourly_rate"] == "150.00"
	assert listing[0]["open_time"] == "00:00"
	assert listing[0]["close_time"] == "23:59"


def test_only_admin_can_create_turf():
	with TestClient(app) as client:
		register_user(client, "customer@example.com")
		customer_token = login_user(client, "customer@example.com")
		customer_response = client.post(
			"/turfs",
			headers={"Authorization": f"Bearer {customer_token}"},
			json={"name": "Customer Turf", "location": "West", "hourly_rate": 100},
		)

		register_user(client, "admin@example.com")
		make_admin("admin@example.com")
		admin_token = login_user(client, "admin@example.com")
		admin_response = client.post(
			"/turfs",
			headers={"Authorization": f"Bearer {admin_token}"},
			json={"name": "Admin Turf", "location": "East", "hourly_rate": 200},
		)

	assert customer_response.status_code == 403
	assert admin_response.status_code == 201
	assert admin_response.json()["name"] == "Admin Turf"


def test_booking_creation_and_my_bookings():
	turf = seed_turf()
	with TestClient(app) as client:
		register_user(client, "booker@example.com")
		token = login_user(client, "booker@example.com")
		headers = {"Authorization": f"Bearer {token}"}
		booking_response = client.post(
			"/bookings/",
			headers=headers,
			json={
				"turf_id": turf.id,
				"booking_date": "2026-09-15",
				"slot_time": "18:00-19:00",
			},
		)
		my_bookings_response = client.get("/bookings/me", headers=headers)

	assert booking_response.status_code == 201
	assert booking_response.json()["status"] == "confirmed"
	assert my_bookings_response.status_code == 200
	assert len(my_bookings_response.json()) == 1
	assert my_bookings_response.json()[0]["id"] == booking_response.json()["id"]


def test_confirmed_slot_cannot_be_booked_twice():
	turf = seed_turf()
	with TestClient(app) as client:
		register_user(client, "first@example.com")
		token = login_user(client, "first@example.com")
		booking_data = {
			"turf_id": turf.id,
			"booking_date": "2026-09-15",
			"slot_time": "18:00-19:00",
		}
		first_response = client.post(
			"/bookings/",
			headers={"Authorization": f"Bearer {token}"},
			json=booking_data,
		)
		second_response = client.post(
			"/bookings/",
			headers={"Authorization": f"Bearer {token}"},
			json=booking_data,
		)

	assert first_response.status_code == 201
	assert second_response.status_code == 400
	assert second_response.json()["detail"] == "Slot is already booked!"


@pytest.mark.parametrize(
	"booking_date,slot_time",
	[
		("2026-02-30", "18:00-19:00"),
		("2026-09-15", "19:00-18:00"),
		("2026-09-15", "25:00-26:00"),
	],
)
def test_invalid_booking_date_or_slot_is_rejected(booking_date: str, slot_time: str):
	turf = seed_turf()
	with TestClient(app) as client:
		register_user(client, "validation@example.com")
		token = login_user(client, "validation@example.com")
		response = client.post(
			"/bookings/",
			headers={"Authorization": f"Bearer {token}"},
			json={
				"turf_id": turf.id,
				"booking_date": booking_date,
				"slot_time": slot_time,
			},
		)

	assert response.status_code == 422


def test_cancelled_slot_can_be_booked_again():
	turf = seed_turf()
	with TestClient(app) as client:
		register_user(client, "rebook@example.com")
		token = login_user(client, "rebook@example.com")
		headers = {"Authorization": f"Bearer {token}"}
		booking_data = {
			"turf_id": turf.id,
			"booking_date": "2026-09-17",
			"slot_time": "18:00-19:00",
		}
		first_booking = client.post("/bookings/", headers=headers, json=booking_data)
		cancel_response = client.patch(
			f"/bookings/{first_booking.json()['id']}/cancel", headers=headers
		)
		second_booking = client.post("/bookings/", headers=headers, json=booking_data)

	assert cancel_response.status_code == 200
	assert second_booking.status_code == 201


def test_only_booking_owner_can_cancel_booking():
	turf = seed_turf()
	with TestClient(app) as client:
		register_user(client, "owner@example.com")
		owner_token = login_user(client, "owner@example.com")
		booking_response = client.post(
			"/bookings/",
			headers={"Authorization": f"Bearer {owner_token}"},
			json={
				"turf_id": turf.id,
				"booking_date": "2026-09-16",
				"slot_time": "19:00-20:00",
			},
		)
		booking_id = booking_response.json()["id"]

		register_user(client, "other@example.com")
		other_token = login_user(client, "other@example.com")
		forbidden_response = client.patch(
			f"/bookings/{booking_id}/cancel",
			headers={"Authorization": f"Bearer {other_token}"},
		)
		cancel_response = client.patch(
			f"/bookings/{booking_id}/cancel",
			headers={"Authorization": f"Bearer {owner_token}"},
		)
		my_bookings_response = client.get(
			"/bookings/me", headers={"Authorization": f"Bearer {owner_token}"}
		)

	assert forbidden_response.status_code == 403
	assert cancel_response.status_code == 200
	assert cancel_response.json()["status"] == "cancelled"
	assert my_bookings_response.json() == []


def test_operating_hours_and_hourly_price_are_applied():
	with TestClient(app) as client:
		register_user(client, "price-admin@example.com")
		make_admin("price-admin@example.com")
		admin_token = login_user(client, "price-admin@example.com")
		turf_response = client.post(
			"/turfs",
			headers={"Authorization": f"Bearer {admin_token}"},
			json={
				"name": "Evening Turf",
				"location": "North",
				"hourly_rate": 100,
				"open_time": "08:00",
				"close_time": "22:00",
			},
		)
		turf_id = turf_response.json()["id"]
		register_user(client, "price-customer@example.com")
		customer_token = login_user(client, "price-customer@example.com")
		booking_response = client.post(
			"/bookings/",
			headers={"Authorization": f"Bearer {customer_token}"},
			json={
				"turf_id": turf_id,
				"booking_date": "2026-10-01",
				"start_time": "18:00",
				"end_time": "20:00",
			},
		)
		outside_hours = client.post(
			"/bookings/",
			headers={"Authorization": f"Bearer {customer_token}"},
			json={
				"turf_id": turf_id,
				"booking_date": "2026-10-02",
				"start_time": "07:00",
				"end_time": "08:00",
			},
		)

	assert booking_response.status_code == 201
	assert booking_response.json()["total_price"] == "200.00"
	assert outside_hours.status_code == 400


def test_customer_can_review_booked_turf_once():
	turf = seed_turf()
	with TestClient(app) as client:
		register_user(client, "reviewer@example.com")
		token = login_user(client, "reviewer@example.com")
		headers = {"Authorization": f"Bearer {token}"}
		booking_response = client.post(
			"/bookings/",
			headers=headers,
			json={
				"turf_id": turf.id,
				"booking_date": "2026-10-04",
				"start_time": "18:00",
				"end_time": "19:00",
			},
		)
		review_response = client.post(
			f"/turfs/{turf.id}/reviews",
			headers=headers,
			json={"rating": 5, "comment": "Excellent turf"},
		)
		duplicate_response = client.post(
			f"/turfs/{turf.id}/reviews",
			headers=headers,
			json={"rating": 4},
		)

	assert booking_response.status_code == 201
	assert review_response.status_code == 201
	assert review_response.json()["rating"] == 5
	assert duplicate_response.status_code == 400


def test_admin_analytics_is_protected_and_reports_counts():
	with TestClient(app) as client:
		register_user(client, "analytics-customer@example.com")
		customer_token = login_user(client, "analytics-customer@example.com")
		unauthorized_response = client.get(
			"/admin/analytics",
			headers={"Authorization": f"Bearer {customer_token}"},
		)
		register_user(client, "analytics-admin@example.com")
		make_admin("analytics-admin@example.com")
		admin_token = login_user(client, "analytics-admin@example.com")
		analytics_response = client.get(
			"/admin/analytics",
			headers={"Authorization": f"Bearer {admin_token}"},
		)

	assert unauthorized_response.status_code == 403
	assert analytics_response.status_code == 200
	assert analytics_response.json()["total_users"] == 2
