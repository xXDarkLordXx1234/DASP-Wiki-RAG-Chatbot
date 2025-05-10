import asyncio
import logging
import signal
from pathlib import Path
from typing import Any

from processor import ClientHandler, Config, logger

logger.setLevel(logging.INFO)


class GracefulExit(SystemExit):
    pass


def shutdown_handler(signum: Any, frame: Any) -> None:
    """
    Shutdown handler for the process_data script.
    """
    raise GracefulExit()


async def main() -> None:
    """
    Main loop for the process_data script.
    """
    config = Config.load(Path("config.yml"))
    if config.logging_file_handler:
        logger.addHandler(config.logging_file_handler)

    logger.info("Starting process_data")
    client_handler = await ClientHandler.build(config=config)

    while True:
        logger.info("Scanning for file changes...")
        try:
            await client_handler.update()
            await asyncio.sleep(config.index.reload_seconds)
        except asyncio.CancelledError:
            logger.info("Update loop cancelled. Shutting down gracefully.")
            break


if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, shutdown_handler)

    try:
        asyncio.run(main())
    except GracefulExit:
        logger.info("Received termination signal. Exiting.")
