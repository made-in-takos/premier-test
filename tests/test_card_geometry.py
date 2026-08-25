from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / "vision"
sys.path.insert(0, str(ROOT))

from card_geometry import find_card_candidates, synthetic_card_frame


def test_synthetic_card_is_detected():
    frame = synthetic_card_frame()
    candidates = find_card_candidates(frame)
    assert len(candidates) >= 1
    assert 1.0 < candidates[0].aspect < 1.8


def test_empty_frame_has_no_card():
    import numpy as np

    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    assert find_card_candidates(frame) == []
