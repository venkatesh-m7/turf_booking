import logging


def setup_logging() -> None:
	logging.basicConfig(
		level=logging.INFO,
		format="%(asctime)s %(levelname)s %(name)s %(message)s",
		handlers=[logging.FileHandler("app.log", encoding="utf-8")],
		force=True,
	)
	logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
