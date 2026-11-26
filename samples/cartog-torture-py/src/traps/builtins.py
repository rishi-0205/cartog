# PATTERN: TRAP-LOGGER-01 — logger.info (builtin, not channel)
import logging
logger = logging.getLogger()
def log(d): logger.info("label", d)
