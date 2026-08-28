# Swagger API Testing Guide

Open Swagger UI:

https://turf-booking-3zfp.onrender.com/docs

Use the endpoints in this order. In Swagger, click **Try it out**, paste the request body, and click **Execute**.

## 1. Check API

### `GET /`

No request body.

Expected response:

```json
{
  "message": "Turf Booking API is running"
}
```

## 2. Register Customer

### `POST /auth/register`

Select **Try it out** and paste:

```json
{
  "email": "customer1@gmail.com",
  "password": "customer1123"
}
```

Expected status: `201 Created`

Save the returned user ID. The role is `customer`.

## 3. Register Admin User

### `POST /auth/register`

Paste:

```json
{
  "email": "admin@gmail.com",
  "password": "admin123"
}
```

New users are customers by default. Admin access must be granted directly in PostgreSQL by changing this user's
`role` to `admin`, or by using the seed script. There is no public admin-promotion endpoint.

## 4. Login Customer

### `POST /auth/login`

This endpoint uses form fields, not JSON.

In Swagger, click **Try it out** and enter:

```text
username: customer1@gmail.com
password: customer1123
```

Copy the returned `access_token`.

## 5. Authorize Swagger

Click the **Authorize** button at the top of Swagger UI.

Enter:

```text
Bearer <customer-access-token>
```

Click **Authorize**, then **Close**.

Now customer-protected endpoints can be tested.

## 6. Login Admin

### `POST /auth/login`

Use:

```text
username: admin@gmail.com
password: admin123
```

Copy the returned `access_token`.

Click **Authorize** again and replace the token with:

```text
Bearer <admin-access-token>
```

Use the admin token for admin-only endpoints.

## 7. Create Turf

### `POST /turfs`

Requires the admin token.

Paste:

```json
{
  "name": "Swagger Football Turf",
  "location": "Downtown",
  "turf_type": "football",
  "open_time": "08:00",
  "close_time": "22:00",
  "hourly_rate": 150
}
```

Copy the returned `id`. This is your `turf_id` for later requests.

Expected important response fields:

```json
{
  "id": 1,
  "name": "Swagger Football Turf",
  "location": "Downtown",
  "turf_type": "football",
  "open_time": "08:00",
  "close_time": "22:00",
  "hourly_rate": "150.00"
}
```

## 8. List Turfs

### `GET /turfs`

This endpoint is public. No authorization is required.

Expected response: a list containing the turf created above.

## 9. Create Booking

Before testing, authorize Swagger with the customer token again.

### `POST /bookings/`

Paste this body. Replace `1` with your actual turf ID if necessary:

```json
{
  "turf_id": 1,
  "booking_date": "2099-06-15",
  "start_time": "18:00",
  "end_time": "19:00"
}
```

Expected response:

```json
{
  "id": 1,
  "user_id": 1,
  "turf_id": 1,
  "booking_date": "2099-06-15",
  "slot_time": "18:00-19:00",
  "start_time": "18:00",
  "end_time": "19:00",
  "status": "confirmed",
  "total_price": "150.00"
}
```

The total is calculated automatically:

```text
1 hour x 150 hourly_rate = 150.00
```

## 10. List My Bookings

### `GET /bookings/me`

Use the customer token. No request body is required.

Expected result: the confirmed booking created above.

## 11. Test Duplicate Booking

### `POST /bookings/`

Submit the exact same body again:

```json
{
  "turf_id": 1,
  "booking_date": "2099-06-15",
  "start_time": "18:00",
  "end_time": "19:00"
}
```

Expected response:

```json
{
  "detail": "Slot is already booked!"
}
```

Expected status: `400 Bad Request`.

## 12. Create Review

Use the customer token. The customer must have booked the turf first.

### `POST /turfs/{turf_id}/reviews`

For `turf_id`, use the ID returned when the turf was created.

Paste:

```json
{
  "rating": 5,
  "comment": "Excellent turf and facilities."
}
```

Expected status: `201 Created`.

A customer can submit only one review for the same turf.

## 13. List Reviews

### `GET /turfs/{turf_id}/reviews`

This endpoint is public. No authorization is required.

Expected result: the review created above.

## 14. Cancel Booking

Use the customer token. The sample booking date is far in the future so it is outside the two-hour cancellation cutoff.

### `PATCH /bookings/{booking_id}/cancel`

Use the booking ID returned by `POST /bookings/`. No request body is required.

Expected response status: `200 OK`.

The returned booking status becomes:

```json
{
  "status": "cancelled"
}
```

Run `GET /bookings/me` again. The cancelled booking will no longer appear because that endpoint returns confirmed bookings only.

## 15. Book the Cancelled Slot Again

### `POST /bookings/`

Use the customer token and submit the same slot again:

```json
{
  "turf_id": 1,
  "booking_date": "2099-06-15",
  "start_time": "18:00",
  "end_time": "19:00"
}
```

Expected status: `201 Created`. Cancelled slots can be booked again.

## 16. Update Turf

Authorize Swagger with the admin token.

### `PATCH /turfs/{turf_id}`

Paste:

```json
{
  "name": "Updated Swagger Football Turf",
  "location": "Central Downtown",
  "turf_type": "football",
  "open_time": "07:00",
  "close_time": "23:00",
  "hourly_rate": 175
}
```

Expected status: `200 OK`.

## 17. Admin Analytics

### `GET /admin/analytics`

Use the admin token. No request body is required.

Expected response shape:

```json
{
  "total_users": 2,
  "total_turfs": 1,
  "total_bookings": 2,
  "confirmed_bookings": 1,
  "cancelled_bookings": 1,
  "total_revenue": "150.00",
  "average_rating": 5.0
}
```

Only confirmed bookings are included in `total_revenue`.

## 18. Admin Booking List

### `GET /admin/bookings`

Use the admin token. This returns confirmed and cancelled bookings.

## 19. Delete Turf

Run this last because deleting the turf also deletes its related bookings and reviews.

### `DELETE /turfs/{turf_id}`

Use the admin token. No request body is required.

Expected status: `204 No Content`.

## Validation Examples

### Invalid date

```json
{
  "turf_id": 1,
  "booking_date": "2026-02-30",
  "start_time": "18:00",
  "end_time": "19:00"
}
```

Expected status: `422 Unprocessable Entity`.

### Outside operating hours

```json
{
  "turf_id": 1,
  "booking_date": "2099-06-20",
  "start_time": "06:00",
  "end_time": "07:00"
}
```

If the turf opens at `08:00`, expected status is `400 Bad Request`.

### Customer attempting an admin endpoint

Authorize Swagger with the customer token and call `POST /turfs` or `GET /admin/analytics`.

Expected status: `403 Forbidden`.

## Authentication Reminder

Use the correct token in Swagger:

```text
Authorize -> Bearer <token> -> Authorize -> Close
```

Only one token is active in Swagger at a time. Re-authorize when switching between customer and admin operations.

## Important

- Do not paste passwords or database URLs into public documentation.
- Use unique email addresses if the same data already exists.
- The Render service must have a valid hosted PostgreSQL `DATABASE_URL`; do not use `localhost` on Render.
- The API creates missing tables at startup. Existing databases should use migrations when schemas change.
