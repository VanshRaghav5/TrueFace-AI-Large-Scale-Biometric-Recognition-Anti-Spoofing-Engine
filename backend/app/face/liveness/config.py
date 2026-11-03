"""Configuration for the ONNX PAD adapter."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PadConfig:
    model_path: Path = Path("models/liveness/pad.onnx")
    input_size: int = 80
    threshold: float = 0.5
    uncertainty_margin: float = 0.05
    model_name: str = "configured_onnx_pad"

    def __post_init__(self) -> None:
        if self.input_size < 8:
            raise ValueError("input_size must be at least 8")
        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError("threshold must be between 0.0 and 1.0")
        if not 0.0 <= self.uncertainty_margin < 0.5:
            raise ValueError("uncertainty_margin must be in [0.0, 0.5)")
