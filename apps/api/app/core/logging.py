import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    level = logging.DEBUG if settings.app_debug else logging.INFO
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )
    handlers: list[logging.Handler] = [logging.StreamHandler()]

    if settings.log_to_file:
        log_path = Path(settings.log_file_path)
        if not log_path.is_absolute():
            project_root = Path(__file__).resolve().parents[3]
            log_path = project_root / log_path
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    for handler in handlers:
        handler.setFormatter(formatter)

    logging.basicConfig(
        level=level,
        handlers=handlers,
        force=True,
    )
