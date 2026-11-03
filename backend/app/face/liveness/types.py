"""Typed PAD result states and outputs."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PadState(str, Enum):
    BONA_FIDE = "bona_fide"
    ATTACK = "attack"
    UNCERTAIN = "uncertain"
    ERROR = "error"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class PadResult:
    state: PadState
    bona_fide_score: Optional[float]
    threshold: Optional[float]
    reason_code: str
    model_name: str
    input_size: int

    @property
    def is_bona_fide(self) -> bool:
        """Return true only for an evaluated, thresholded bona-fide result."""
        return self.state is PadState.BONA_FIDE
