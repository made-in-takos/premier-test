"""
Reconnaissance de carte a jouer avec OpenCV
===========================================

Pipeline (approche EdjeElectronics, adaptee Raspberry Pi) :
  1. Pretraitement (gris + flou + seuillage)
  2. Contour a 4 cotes
  3. Correction de perspective -> carte a plat 200x300
  4. Extraction du coin haut-gauche (rang + couleur)
  5. Comparaison absdiff aux images de reference

MediaPipe n'est pas utilise.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

CARD_WIDTH = 200
CARD_HEIGHT = 300

CORNER_WIDTH = 32
CORNER_HEIGHT = 84
CORNER_ZOOM = 4

RANK_WIDTH = 70
RANK_HEIGHT = 125
SUIT_WIDTH = 70
SUIT_HEIGHT = 100

BKG_THRESH = 60
CARD_THRESH = 30
MIN_CARD_AREA = 5000

# Au-dela, le match est trop mauvais : on affiche Unknown.
RANK_SCORE_MAX = 2500
SUIT_SCORE_MAX = 700

RANKS = ["Ace", "2", "3", "4", "5", "6", "7", "8", "9", "10", "Jack", "Queen", "King"]
SUITS = ["Spades", "Hearts", "Clubs", "Diamonds"]

ROOT = Path(__file__).resolve().parents[1]
REF_RANK_DIR = ROOT / "references" / "ranks"
REF_SUIT_DIR = ROOT / "references" / "suits"


def preprocess_image(image: np.ndarray) -> np.ndarray:
    """Isole les objets clairs (carte) sur fond plus sombre."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    img_h, img_w = gray.shape
    bkg_level = int(gray[int(img_h / 100), int(img_w / 2)])
    thresh_level = bkg_level + BKG_THRESH
    _, thresh = cv2.threshold(blur, thresh_level, 255, cv2.THRESH_BINARY)
    return thresh


def find_card_contour(thresh_image: np.ndarray) -> np.ndarray | None:
    """Plus grand quadrilatere au-dessus de MIN_CARD_AREA."""
    contours, _ = cv2.findContours(thresh_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < MIN_CARD_AREA:
            break
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        if len(approx) == 4:
            return approx.reshape(4, 2)
    return None


def order_points(pts: np.ndarray) -> np.ndarray:
    """Ordonne 4 points : haut-gauche, haut-droite, bas-droite, bas-gauche."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def flatten_card(image: np.ndarray, points: np.ndarray) -> np.ndarray:
    """Vue a plat en portrait (rang attendu dans un coin)."""
    rect = order_points(points.astype("float32"))
    width_top = float(np.linalg.norm(rect[1] - rect[0]))
    width_bot = float(np.linalg.norm(rect[2] - rect[3]))
    height_left = float(np.linalg.norm(rect[3] - rect[0]))
    height_right = float(np.linalg.norm(rect[2] - rect[1]))
    width = max(width_top, width_bot)
    height = max(height_left, height_right)
    if width > height:
        rect = np.array([rect[1], rect[2], rect[3], rect[0]], dtype="float32")
    dst = np.array(
        [
            [0, 0],
            [CARD_WIDTH - 1, 0],
            [CARD_WIDTH - 1, CARD_HEIGHT - 1],
            [0, CARD_HEIGHT - 1],
        ],
        dtype="float32",
    )
    matrix = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(image, matrix, (CARD_WIDTH, CARD_HEIGHT))


def isolate_symbol(region: np.ndarray, target_w: int, target_h: int) -> np.ndarray | None:
    """Recadre le plus grand blob puis le met a la taille des references."""
    contours, _ = cv2.findContours(region, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    biggest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(biggest) < 20:
        return None
    x, y, w, h = cv2.boundingRect(biggest)
    roi = region[y : y + h, x : x + w]
    if roi.size == 0:
        return None
    return cv2.resize(roi, (target_w, target_h))


def extract_corner(warped_card: np.ndarray) -> tuple[np.ndarray | None, np.ndarray | None]:
    """Rang (haut du coin) et couleur (bas du coin)."""
    corner = warped_card[0:CORNER_HEIGHT, 0:CORNER_WIDTH]
    corner_zoom = cv2.resize(corner, (0, 0), fx=CORNER_ZOOM, fy=CORNER_ZOOM)
    gray = cv2.cvtColor(corner_zoom, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    white_level = int(gray[15, int((CORNER_WIDTH * CORNER_ZOOM) / 2)])
    thresh_level = white_level - CARD_THRESH
    if thresh_level <= 0:
        thresh_level = 1
    _, thresh = cv2.threshold(blur, thresh_level, 255, cv2.THRESH_BINARY_INV)

    zoom_h = CORNER_HEIGHT * CORNER_ZOOM
    zoom_w = CORNER_WIDTH * CORNER_ZOOM
    rank_split = int(zoom_h * 0.55)
    rank_region = thresh[20:rank_split, 0:zoom_w]
    suit_region = thresh[rank_split + 1 : zoom_h, 0:zoom_w]
    return isolate_symbol(rank_region, RANK_WIDTH, RANK_HEIGHT), isolate_symbol(
        suit_region, SUIT_WIDTH, SUIT_HEIGHT
    )


def load_references(
    rank_dir: Path | None = None,
    suit_dir: Path | None = None,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    rank_dir = Path(rank_dir) if rank_dir else REF_RANK_DIR
    suit_dir = Path(suit_dir) if suit_dir else REF_SUIT_DIR
    rank_refs: dict[str, np.ndarray] = {}
    suit_refs: dict[str, np.ndarray] = {}
    for rank in RANKS:
        path = rank_dir / f"{rank}.jpg"
        if not path.exists():
            continue
        image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if image is not None:
            rank_refs[rank] = cv2.resize(image, (RANK_WIDTH, RANK_HEIGHT))
    for suit in SUITS:
        path = suit_dir / f"{suit}.jpg"
        if not path.exists():
            continue
        image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if image is not None:
            suit_refs[suit] = cv2.resize(image, (SUIT_WIDTH, SUIT_HEIGHT))
    return rank_refs, suit_refs


def match_symbol(candidate: np.ndarray | None, references: dict[str, np.ndarray]) -> tuple[str, float]:
    if candidate is None or not references:
        return "Unknown", float("inf")
    best_match = "Unknown"
    best_score = float("inf")
    for name, ref_image in references.items():
        if ref_image.shape != candidate.shape:
            ref_image = cv2.resize(ref_image, (candidate.shape[1], candidate.shape[0]))
        diff = cv2.absdiff(candidate, ref_image)
        score = float(np.sum(diff) / 255.0)
        if score < best_score:
            best_score = score
            best_match = name
    return best_match, best_score


def _score_orientation(
    warped: np.ndarray,
    rank_refs: dict[str, np.ndarray],
    suit_refs: dict[str, np.ndarray],
) -> dict:
    rank_img, suit_img = extract_corner(warped)
    rank, rank_score = match_symbol(rank_img, rank_refs)
    suit, suit_score = match_symbol(suit_img, suit_refs)
    return {
        "rank": rank,
        "suit": suit,
        "rank_score": rank_score,
        "suit_score": suit_score,
        "rank_img": rank_img,
        "suit_img": suit_img,
        "warped_card": warped,
    }


def identify_card(
    image: np.ndarray,
    rank_refs: dict[str, np.ndarray],
    suit_refs: dict[str, np.ndarray],
) -> dict | None:
    """Renvoie rang/couleur, ou None si aucun quadrilatere n'est trouve."""
    thresh = preprocess_image(image)
    contour = find_card_contour(thresh)
    if contour is None:
        return None
    warped = flatten_card(image, contour)
    upright = _score_orientation(warped, rank_refs, suit_refs)
    flipped = _score_orientation(cv2.rotate(warped, cv2.ROTATE_180), rank_refs, suit_refs)
    chosen = upright if (upright["rank_score"] + upright["suit_score"]) <= (
        flipped["rank_score"] + flipped["suit_score"]
    ) else flipped
    if chosen["rank_score"] > RANK_SCORE_MAX:
        chosen["rank"] = "Unknown"
    if chosen["suit_score"] > SUIT_SCORE_MAX:
        chosen["suit"] = "Unknown"
    chosen["contour"] = contour
    return chosen
