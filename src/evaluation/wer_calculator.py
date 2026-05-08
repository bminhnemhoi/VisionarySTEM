"""
VisionarySTEM - WER/CER Calculator
====================================
Sprint 2: Hungarian assignment for global-optimal block matching
(replaces greedy lowest-CER which biased results when AI emitted extra blocks).

Tinh WER/CER + ghep cap GT vs AI bang Hungarian (toi uu toan cuc).
"""

import logging
import re
from typing import Dict, List, Tuple

import jiwer
import numpy as np
from scipy.optimize import linear_sum_assignment

logger = logging.getLogger(__name__)


def preprocess_vietnamese_text(text: str) -> str:
    """
    Standardize Vietnamese text for WER calculation:
    - Lowercase
    - Remove punctuation
    - Collapse whitespace
    """
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def calculate_wer_cer(reference: str, hypothesis: str) -> Tuple[float, float]:
    """Tính WER và CER. Trả (wer, cer) clamp [0, 1]."""
    ref = preprocess_vietnamese_text(reference)
    hyp = preprocess_vietnamese_text(hypothesis)
    if not ref and not hyp:
        return 0.0, 0.0
    if not ref:
        return 1.0, 1.0
    try:
        wer = float(jiwer.wer(ref, hyp))
        cer = float(jiwer.cer(ref, hyp))
        return min(wer, 1.0), min(cer, 1.0)
    except ValueError as e:
        logger.warning(f"WER calculation failed: {e}")
        return 1.0, 1.0


def _build_cost_matrix(
    gt_blocks: List[Dict],
    ai_blocks: List,
) -> np.ndarray:
    """Cost[i][j] = CER between GT i and AI j; dummy padded to square."""
    n_gt = len(gt_blocks)
    n_ai = len(ai_blocks)
    n = max(n_gt, n_ai)
    cost = np.ones((n, n), dtype=np.float64)  # default = 1.0 for unmatched (worst)

    for i, gt in enumerate(gt_blocks):
        ref = gt.get("spoken_text", "")
        for j, ai in enumerate(ai_blocks):
            hyp = ai.get("spoken_text", "") if isinstance(ai, dict) else ai.spoken_text
            _, cer = calculate_wer_cer(ref, hyp)
            cost[i, j] = cer
    return cost


def evaluate_document_accuracy(
    ground_truth_blocks: List[Dict],
    ai_generated_blocks: List,
) -> Dict:
    """
    Hungarian-optimal matching of GT ↔ AI blocks by CER, then aggregate WER/CER per type.

    Returns:
        {
            "overall": {"wer": float, "cer": float, "count": int, "unmatched_gt": int, "extra_ai": int},
            "by_type": {type: {wer, cer, count}}
        }
    """
    n_gt = len(ground_truth_blocks)
    n_ai = len(ai_generated_blocks)

    if n_gt == 0:
        return {
            "overall": {"wer": 0.0, "cer": 0.0, "count": 0, "unmatched_gt": 0, "extra_ai": n_ai},
            "by_type": {},
        }

    cost_matrix = _build_cost_matrix(ground_truth_blocks, ai_generated_blocks)
    # Hungarian: minimize total CER
    row_ind, col_ind = linear_sum_assignment(cost_matrix)

    results = {
        "overall": {"wer": 0.0, "cer": 0.0, "count": 0, "unmatched_gt": 0, "extra_ai": 0},
        "by_type": {},
    }

    total_wer = 0.0
    total_cer = 0.0
    matched_count = 0

    for i, j in zip(row_ind, col_ind):
        if i >= n_gt:
            # Dummy GT → extra AI block
            results["overall"]["extra_ai"] += 1
            continue
        gt = ground_truth_blocks[i]
        b_type = gt.get("type", "text")
        ref_text = gt.get("spoken_text", "")

        if j >= n_ai:
            # Unmatched GT (no AI block) → 100% error
            wer, cer = 1.0, 1.0
            results["overall"]["unmatched_gt"] += 1
        else:
            ai = ai_generated_blocks[j]
            hyp_text = ai.get("spoken_text", "") if isinstance(ai, dict) else ai.spoken_text
            wer, cer = calculate_wer_cer(ref_text, hyp_text)

        if b_type not in results["by_type"]:
            results["by_type"][b_type] = {"wer": 0.0, "cer": 0.0, "count": 0}
        results["by_type"][b_type]["wer"] += wer
        results["by_type"][b_type]["cer"] += cer
        results["by_type"][b_type]["count"] += 1
        total_wer += wer
        total_cer += cer
        matched_count += 1

    if matched_count > 0:
        results["overall"]["wer"] = total_wer / matched_count
        results["overall"]["cer"] = total_cer / matched_count
        results["overall"]["count"] = matched_count
        for b_type, agg in results["by_type"].items():
            if agg["count"] > 0:
                agg["wer"] /= agg["count"]
                agg["cer"] /= agg["count"]

    # Count extra AI blocks not assigned to any GT
    if n_ai > n_gt:
        results["overall"]["extra_ai"] = n_ai - n_gt

    return results
