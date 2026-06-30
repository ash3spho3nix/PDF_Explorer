"""
Centralized logging layout utilizing Rich handling for structured terminal output.
"""

import logging
from rich.logging import RichHandler


def get_logger(name: str = "pdfscan") -> logging.Logger:
    """
    Retrieves or configures a standard logging facility integrated with Rich rendering.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        rich_handler = RichHandler(
            level=logging.INFO,
            show_time=False,
            show_path=False,
            markup=True
        )
        formatter = logging.Formatter("%(message)s")
        rich_handler.setFormatter(formatter)
        logger.addHandler(rich_handler)
    return logger