"""Test WER/CER + Hungarian matching."""
import pytest


def test_preprocess_strips_punctuation():
    from src.evaluation.wer_calculator import preprocess_vietnamese_text
    assert preprocess_vietnamese_text("Hello, World!") == "hello world"
    assert preprocess_vietnamese_text("  Định    luật.  ") == "định luật"
    assert preprocess_vietnamese_text("") == ""
    assert preprocess_vietnamese_text(None) == ""


def test_calculate_wer_perfect_match():
    from src.evaluation.wer_calculator import calculate_wer_cer
    wer, cer = calculate_wer_cer("xin chào việt nam", "xin chào việt nam")
    assert wer == 0.0
    assert cer == 0.0


def test_calculate_wer_completely_wrong():
    from src.evaluation.wer_calculator import calculate_wer_cer
    wer, cer = calculate_wer_cer("một hai ba", "bốn năm sáu")
    assert wer == 1.0


def test_empty_inputs():
    from src.evaluation.wer_calculator import calculate_wer_cer
    assert calculate_wer_cer("", "") == (0.0, 0.0)
    assert calculate_wer_cer("", "anything") == (1.0, 1.0)


def test_hungarian_matching_perfect():
    """When AI emits same blocks as GT in different order, Hungarian should still get 0% WER."""
    from src.evaluation.wer_calculator import evaluate_document_accuracy

    gt = [
        {"id": "g1", "type": "text", "spoken_text": "câu một"},
        {"id": "g2", "type": "math", "spoken_text": "công thức hai"},
    ]
    # AI emits in reverse order
    ai = [
        {"id": "a1", "type": "math", "spoken_text": "công thức hai"},
        {"id": "a2", "type": "text", "spoken_text": "câu một"},
    ]
    result = evaluate_document_accuracy(gt, ai)
    assert result["overall"]["wer"] == 0.0
    assert result["overall"]["count"] == 2


def test_hungarian_matching_extra_ai():
    """Extra AI blocks should be counted as extra_ai, not bias matched WER."""
    from src.evaluation.wer_calculator import evaluate_document_accuracy

    gt = [{"id": "g1", "type": "text", "spoken_text": "câu một"}]
    ai = [
        {"id": "a1", "type": "text", "spoken_text": "câu một"},  # match
        {"id": "a2", "type": "text", "spoken_text": "rác thải"},  # extra
    ]
    result = evaluate_document_accuracy(gt, ai)
    assert result["overall"]["wer"] == 0.0
    assert result["overall"]["extra_ai"] >= 1


def test_hungarian_unmatched_gt():
    """Missing AI blocks → unmatched_gt counter should bump."""
    from src.evaluation.wer_calculator import evaluate_document_accuracy

    gt = [
        {"id": "g1", "type": "text", "spoken_text": "câu một"},
        {"id": "g2", "type": "math", "spoken_text": "công thức hai"},
    ]
    ai = [{"id": "a1", "type": "text", "spoken_text": "câu một"}]
    result = evaluate_document_accuracy(gt, ai)
    assert result["overall"]["unmatched_gt"] == 1
    assert result["overall"]["count"] == 2
    # Unmatched GT contributes 1.0 WER → average should be 0.5
    assert result["overall"]["wer"] == pytest.approx(0.5, abs=0.01)


def test_empty_gt():
    from src.evaluation.wer_calculator import evaluate_document_accuracy
    result = evaluate_document_accuracy([], [{"type": "text", "spoken_text": "x"}])
    assert result["overall"]["count"] == 0
    assert result["overall"]["extra_ai"] == 1
