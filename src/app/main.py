"""
Main application entry point for stock-tech-volatility.

This module initializes logging and starts the queue message processing loop.
"""

from app.queue_handler import consume_messages
from app.logger import setup_logger

# Set up logger for this module
logger = setup_logger("main")


def main() -> None:
    """
    Starts the volatility analysis message processing loop.
    """
    logger.info("Starting stock-tech-volatility processor...")
    try:
        consume_messages()
    except KeyboardInterrupt:
        logger.info("Volatility processor stopped by user.")
    except Exception as e:
        logger.exception("Fatal error occurred: %s", str(e))


if __name__ == "__main__":
    main()
