"""Main application entry point for stock-tech-volatility.

This module initializes logging and starts the queue message processing
loop.
"""

from app.logger import setup_logger
from app.queue_handler import consume_messages

# Set up logger for this module
logger = setup_logger("main")


def main() -> None:
    """Starts the volatility analysis message processing loop.

    This function will block until the user stops the service (e.g. Ctrl-C).

    :return: None

    Args:

    Returns:
    """
    logger.info("Starting stock-tech-volatility processor...")

    try:
        # Start consuming messages from the specified queue
        consume_messages()  # type: ignore
    except KeyboardInterrupt:
        # User stopped the service, exit cleanly
        logger.info("Volatility processor stopped by user.")
    except Exception as e:
        # Fatal error occurred, log exception and exit
        logger.exception("Fatal error occurred: %s", str(e))


if __name__ == "__main__":
    main()
