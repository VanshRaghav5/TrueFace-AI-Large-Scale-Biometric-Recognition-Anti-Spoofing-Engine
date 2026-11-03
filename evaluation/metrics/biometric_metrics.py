import numpy as np
from typing import Tuple, Dict

def compute_eer(genuine_scores: np.ndarray, impostor_scores: np.ndarray) -> Tuple[float, float]:
    """
    Computes Equal Error Rate (EER) and operating threshold from genuine and impostor similarity scores.
    """
    thresholds = np.linspace(0.0, 1.0, 1000)
    far_list = []
    frr_list = []

    for t in thresholds:
        frr = np.mean(genuine_scores < t)
        far = np.mean(impostor_scores >= t)
        far_list.append(far)
        frr_list.append(frr)

    far_arr = np.array(far_list)
    frr_arr = np.array(frr_list)
    min_idx = np.argmin(np.abs(far_arr - frr_arr))

    eer = float((far_arr[min_idx] + frr_arr[min_idx]) / 2.0)
    eer_threshold = float(thresholds[min_idx])
    return eer, eer_threshold

def compute_pad_metrics(bona_fide_scores: np.ndarray, attack_scores: np.ndarray, threshold: float) -> Dict[str, float]:
    """
    Computes ISO/IEC 30107-3 PAD metrics:
    - APCER (Attack Presentation Classification Error Rate)
    - BPCER (Bona Fide Presentation Classification Error Rate)
    """
    apcer = float(np.mean(attack_scores >= threshold))
    bpcer = float(np.mean(bona_fide_scores < threshold))
    return {
        "apcer": apcer,
        "bpcer": bpcer,
        "acer": (apcer + bpcer) / 2.0
    }

