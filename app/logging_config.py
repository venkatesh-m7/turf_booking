import logging
from logging.handlers import RotatingFileHandler

from app.config import settings


def setup_logging() -> None:
	log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
	formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

	file_handler = RotatingFileHandler(
		"app.log",
		maxBytes=5 * 1024 * 1024,
		backupCount=3,
		encoding="utf-8",
	)

	console_handler = logging.StreamHandler()
	file_handler.setFormatter(formatter)
	console_handler.setFormatter(formatter)
	logging.basicConfig(
		level=log_level,
		handlers=[file_handler, console_handler],
		force=True,
	)
	logging.getLogger("sqlalchemy.engine").setLevel(log_level)
	logging.getLogger("urllib3").setLevel(logging.WARNING)
