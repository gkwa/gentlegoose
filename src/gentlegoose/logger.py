import logging
import sys


def setup_logging(verbosity: int) -> None:
    """Setup logging configuration based on verbosity level."""
    if verbosity == 0:
        level = logging.WARNING
    elif verbosity == 1:
        level = logging.INFO
    else:
        level = logging.DEBUG

    logging.basicConfig(
        level=level, format="%(levelname)s: %(message)s", stream=sys.stderr
    )
