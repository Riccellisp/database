import logging
import sys

# Configure standard logging to output straight to stdout without extra prefixes,
# allowing our custom format to be clean and simple.
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("monitoring_service")

def info(equipamento_id: int, msg: str):
    logger.info(f"equipamento={equipamento_id} {msg}")

def warn(equipamento_id: int, msg: str):
    logger.warning(f"equipamento={equipamento_id} {msg}")

def error(equipamento_id: int, msg: str):
    logger.error(f"equipamento={equipamento_id} {msg}")
