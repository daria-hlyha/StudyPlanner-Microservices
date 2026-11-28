
"""
Централізоване налаштування журналювання Study Plan Service.

Модуль забезпечує єдиний формат повідомлень журналу
та стандартний рівень журналювання застосунку.
"""

import logging
import time

from logging.config import dictConfig


# ==========================================================
# 1. ФОРМАТУВАННЯ ПОВІДОМЛЕНЬ
# ==========================================================

class UTCFormatter(logging.Formatter):
    """Форматування часу журналу в UTC."""

    converter = time.gmtime


# ==========================================================
# 2. НАЛАШТУВАННЯ ЖУРНАЛЮВАННЯ
# ==========================================================

def configure_logging() -> None:
    """Налаштування стандартного журналювання мікросервісу."""

    dictConfig({
        "version": 1,

        "disable_existing_loggers": False,

        "formatters": {
            "standard": {
                "()": UTCFormatter,

                "format": (
                    "%(asctime)sZ | "
                    "%(levelname)s | "
                    "%(name)s | "
                    "%(message)s"
                ),

                "datefmt": "%Y-%m-%dT%H:%M:%S"
            }
        },

        "handlers": {
            "console": {
                "class": "logging.StreamHandler",

                "formatter": "standard",

                "stream": "ext://sys.stdout"
            }
        },

        "root": {
            "handlers": ["console"],

            "level": "INFO"
        },

        "loggers": {
            "pika": {
                "level": "WARNING"
            }
        }
    })
