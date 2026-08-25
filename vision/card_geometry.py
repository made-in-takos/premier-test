"""Detection de contours de cartes a jouer avec OpenCV (sans MediaPipe)."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

# Ratio hauteur/largeur d'une carte poker standard (~88.9 x 63.5 mm).
CARD_ASPECT = 88.9 / 63.5
ASPECT_TOLERANCE = 0.35


@dataclass(frozen=True)
class CardCandidate:
    contour: np.ndarray
    approx: np.ndarray
    area: float
    aspect: float


def preprocess(frame: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    return cv2.Canny(blur, 60, 180)


def _aspect_ratio(approx: np.ndarray) -> float:
    rect = cv2.minAreaRect(approx)
    width, height = rect[1]
    if min(width, height) < 1:
        return 0.0
    return max(width, height) / min(width, height)


def find_card_candidates(
    frame: np.ndarray,
    min_area_ratio: float = 0.02,
    max_area_ratio: float = 0.8,
) -> list[CardCandidate]:
    """Retourne les quadrilateres dont le ratio ressemble a une carte."""
    edges = preprocess(frame)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    image_area = float(frame.shape[0] * frame.shape[1])
    found: list[CardCandidate] = []

    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < min_area_ratio * image_area or area > max_area_ratio * image_area:
            continue
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        if len(approx) != 4:
            continue
        aspect = _aspect_ratio(approx)
        if abs(aspect - CARD_ASPECT) > ASPECT_TOLERANCE:
            continue
        found.append(CardCandidate(contour=contour, approx=approx, area=area, aspect=aspect))

    found.sort(key=lambda item: item.area, reverse=True)
    return found


def draw_candidates(frame: np.ndarray, candidates: list[CardCandidate]) -> np.ndarray:
    output = frame.copy()
    for index, candidate in enumerate(candidates, start=1):
        cv2.drawContours(output, [candidate.approx], -1, (0, 255, 0), 2)
        x, y, _, _ = cv2.boundingRect(candidate.approx)
        label = f"carte {index}  ratio={candidate.aspect:.2f}"
        cv2.putText(output, label, (x, max(20, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    return output


def synthetic_card_frame(width: int = 640, height: int = 480) -> np.ndarray:
    """Image de test: rectangle blanc aux proportions d'une carte sur fond sombre."""
    frame = np.full((height, width, 3), 30, dtype=np.uint8)
    card_w, card_h = 180, 252
    x = (width - card_w) // 2
    y = (height - card_h) // 2
    cv2.rectangle(frame, (x, y), (x + card_w, y + card_h), (245, 245, 245), thickness=-1)
    cv2.rectangle(frame, (x, y), (x + card_w, y + card_h), (10, 10, 10), thickness=3)
    return frame
