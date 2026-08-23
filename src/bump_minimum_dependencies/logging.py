__all__ = ["logger"]

import logging



logger = logging.getLogger("bump")
logger.propagate = True
logger.setLevel(logging.WARNING)
