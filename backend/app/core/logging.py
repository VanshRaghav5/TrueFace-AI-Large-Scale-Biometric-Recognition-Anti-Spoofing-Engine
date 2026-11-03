import logging
import sys
from typing import Any, Dict

def mask_embedding(vector_repr: Any) -> str:
    """Mask embedding vectors in logs to ensure privacy-by-default."""
    if vector_repr is None:
        return "None"
    return "<MASKED_512D_FLOAT_VECTOR>"

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )

logger = logging.getLogger("trueface")

