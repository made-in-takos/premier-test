from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1] / "python"
sys.path.insert(0, str(ROOT))

from identify import (
    CARD_HEIGHT,
    CARD_WIDTH,
    RANK_HEIGHT,
    RANK_WIDTH,
    SUIT_HEIGHT,
    SUIT_WIDTH,
    flatten_card,
    identify_card,
    isolate_symbol,
    load_references,
    match_symbol,
    order_points,
)


def test_order_points_axis_aligned():
    pts = np.array([[80, 40], [10, 200], [10, 40], [80, 200]], dtype="float32")
    ordered = order_points(pts)
    np.testing.assert_array_equal(ordered[0], [10, 40])
    np.testing.assert_array_equal(ordered[1], [80, 40])
    np.testing.assert_array_equal(ordered[2], [80, 200])
    np.testing.assert_array_equal(ordered[3], [10, 200])


def test_flatten_card_output_size():
    image = np.zeros((240, 320, 3), dtype=np.uint8)
    pts = np.array([[40, 20], [200, 20], [200, 220], [40, 220]], dtype="float32")
    warped = flatten_card(image, pts)
    assert warped.shape == (CARD_HEIGHT, CARD_WIDTH, 3)


def test_isolate_symbol_resizes_to_target():
    region = np.zeros((80, 60), dtype=np.uint8)
    cv2.rectangle(region, (10, 8), (40, 60), 255, thickness=-1)
    out = isolate_symbol(region, RANK_WIDTH, RANK_HEIGHT)
    assert out is not None
    assert out.shape == (RANK_HEIGHT, RANK_WIDTH)


def test_match_symbol_picks_closest_reference():
    ace = np.zeros((RANK_HEIGHT, RANK_WIDTH), dtype=np.uint8)
    cv2.putText(ace, "A", (8, 100), cv2.FONT_HERSHEY_SIMPLEX, 3, 255, 8)
    king = np.zeros((RANK_HEIGHT, RANK_WIDTH), dtype=np.uint8)
    cv2.putText(king, "K", (8, 100), cv2.FONT_HERSHEY_SIMPLEX, 3, 255, 8)
    name, _score = match_symbol(ace, {"Ace": ace, "King": king})
    assert name == "Ace"


def _synthetic_marked_card() -> np.ndarray:
    frame = np.full((480, 640, 3), 20, dtype=np.uint8)
    x, y, w, h = 220, 90, 180, 252
    cv2.rectangle(frame, (x, y), (x + w, y + h), (250, 250, 250), thickness=-1)
    cv2.rectangle(frame, (x + 6, y + 8), (x + 24, y + 48), (10, 10, 10), thickness=-1)
    cv2.circle(frame, (x + 16, y + 68), 8, (10, 10, 10), thickness=-1)
    return frame


def test_identify_card_matches_saved_references(tmp_path: Path):
    frame = _synthetic_marked_card()
    rank_dir = tmp_path / "ranks"
    suit_dir = tmp_path / "suits"
    rank_dir.mkdir()
    suit_dir.mkdir()

    first = identify_card(frame, {}, {})
    assert first is not None
    assert first["rank_img"] is not None
    assert first["suit_img"] is not None
    cv2.imwrite(str(rank_dir / "Ace.jpg"), first["rank_img"])
    cv2.imwrite(str(suit_dir / "Spades.jpg"), first["suit_img"])
    dummy_rank = np.zeros((RANK_HEIGHT, RANK_WIDTH), dtype=np.uint8)
    dummy_suit = np.zeros((SUIT_HEIGHT, SUIT_WIDTH), dtype=np.uint8)
    cv2.imwrite(str(rank_dir / "King.jpg"), dummy_rank)
    cv2.imwrite(str(suit_dir / "Hearts.jpg"), dummy_suit)

    rank_refs, suit_refs = load_references(rank_dir, suit_dir)
    result = identify_card(frame, rank_refs, suit_refs)
    assert result is not None
    assert result["rank"] == "Ace"
    assert result["suit"] == "Spades"


def test_identify_card_empty_background():
    frame = np.full((240, 320, 3), 20, dtype=np.uint8)
    assert identify_card(frame, {}, {}) is None
