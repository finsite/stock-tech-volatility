"""
Module to handle logging for Ichimoku Analysis Service.

This module sets up a logger with a standard format and INFO level.
"""

import logging


def setup_logger(name: str = "ichimoku") -> logging.Logger:
    """
    Sets up a logger with a standard format and INFO level.

    Args:
    ----
        name (str): Name of the logger. Defaults to "ichimoku".

    Returns:
    -------
        logging.Logger: Configured logger instance with a stream handler and formatter.

    Notes:
    -----
        This function sets up a logger with a standard format and INFO level.
        If the logger does not already have handlers, it will be configured.
        If the logger already has handlers, they will not be overridden.
    """
    logger: logging.Logger = logging.getLogger(name)

    if not logger.hasHandlers():
        handler: logging.StreamHandler = logging.StreamHandler()
        formatter: logging.Formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger
