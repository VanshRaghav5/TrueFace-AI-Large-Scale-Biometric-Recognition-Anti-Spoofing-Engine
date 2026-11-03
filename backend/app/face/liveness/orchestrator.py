"""Application boundary for converting PAD failures into explicit states."""

from __future__ import annotations

from typing import Callable

import numpy as np

from .exceptions import PadError, PadInputError, PadModelUnavailableError
from .types import PadResult, PadState


class PadOrchestrator:
    """Keep component exceptions from becoming a bona-fide result."""

    def __init__(self, model_name: str, input_size: int = 80) -> None:
        self.model_name = model_name
        self.input_size = input_size

    def evaluate(self, operation: Callable[[], PadResult]) -> PadResult:
        try:
            result = operation()
        except PadModelUnavailableError:
            return PadResult(
                PadState.UNAVAILABLE,
                None,
                None,
                "PAD_MODEL_UNAVAILABLE",
                self.model_name,
                self.input_size,
            )
        except (PadInputError, PadError):
            return PadResult(
                PadState.ERROR,
                None,
                None,
                "PAD_EVALUATION_ERROR",
                self.model_name,
                self.input_size,
            )
        except Exception as exc:
            return PadResult(
                PadState.ERROR,
                None,
                None,
                f"PAD_UNEXPECTED_ERROR:{type(exc).__name__}",
                self.model_name,
                self.input_size,
            )
        if result.state is PadState.BONA_FIDE and result.bona_fide_score is None:
            return PadResult(
                PadState.ERROR,
                None,
                result.threshold,
                "PAD_INVALID_RESULT",
                self.model_name,
                self.input_size,
            )
        return result

    def classify_score(
        self,
        score: float,
        threshold: float,
        uncertainty_margin: float,
    ) -> PadResult:
        """Create an explicit result from a calibrated model score."""
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0.0 and 1.0")
        if not 0.0 <= uncertainty_margin < 0.5:
            raise ValueError("uncertainty_margin must be in [0.0, 0.5)")
        if not np.isfinite(score) or not 0.0 <= score <= 1.0:
            return PadResult(
                PadState.ERROR,
                None,
                threshold,
                "PAD_INVALID_SCORE",
                self.model_name,
                self.input_size,
            )
        if abs(score - threshold) < uncertainty_margin:
            state, reason = PadState.UNCERTAIN, "PAD_SCORE_UNCERTAIN"
        elif score >= threshold:
            state, reason = PadState.BONA_FIDE, "PAD_BONA_FIDE"
        else:
            state, reason = PadState.ATTACK, "PAD_ATTACK_RISK"
        return PadResult(
            state,
            score,
            threshold,
            reason,
            self.model_name,
            self.input_size,
        )
