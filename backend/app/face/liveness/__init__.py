"""Face presentation-attack detection interfaces."""

from .config import PadConfig
from .antispoof_mn3 import (
    AntiSpoofMn3Config,
    AntiSpoofMn3Engine,
    AntiSpoofMn3RawResult,
    antispoof_mn3_tensor,
)
from .exceptions import (
    PadError,
    PadInferenceError,
    PadInputError,
    PadModelUnavailableError,
    PadOutputContractError,
)
from .minifasnet import MiniFASNetConfig, MiniFASNetEnsemble, MiniFASNetPrediction
from .onnx_pad import OnnxPadEngine
from .orchestrator import PadOrchestrator
from .types import PadResult, PadState

__all__ = [
    "OnnxPadEngine",
    "AntiSpoofMn3Config",
    "AntiSpoofMn3Engine",
    "AntiSpoofMn3RawResult",
    "antispoof_mn3_tensor",
    "PadConfig",
    "PadError",
    "PadInferenceError",
    "PadInputError",
    "PadModelUnavailableError",
    "PadOutputContractError",
    "MiniFASNetConfig",
    "MiniFASNetEnsemble",
    "MiniFASNetPrediction",
    "PadResult",
    "PadState",
    "PadOrchestrator",
]
