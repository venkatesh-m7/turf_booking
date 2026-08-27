import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.database import Base, engine
from app.logging_config import setup_logging
from app.routers import admin_router, auth_router, booking_router, turf_router

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
	Base.metadata.create_all(bind=engine)
	yield


app = FastAPI(title="Turf Booking API", lifespan=lifespan)


@app.middleware("http")
async def log_requests(request: Request, call_next):
	logger.info("Incoming request: %s %s", request.method, request.url.path)
	return await call_next(request)


@app.get("/")
def root() -> dict[str, str]:
	return {"message": "Turf Booking API is running"}


app.include_router(auth_router.router)
app.include_router(turf_router.router)
app.include_router(booking_router.router)
app.include_router(admin_router.router)
