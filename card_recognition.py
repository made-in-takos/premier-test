"""
Reconnaissance de carte à jouer avec OpenCV
============================================

Pipeline :
  1. Prétraitement de l'image (gris + flou + seuillage)
  2. Détection du contour de la carte (le plus grand rectangle)
  3. Correction de perspective -> image "à plat" de taille fixe
  4. Extraction du coin haut-gauche (rang + symbole)
  5. Comparaison à une bibliothèque de références (rangs + couleurs)

Auteur de référence : approche inspirée du tutoriel EdjeElectronics
"OpenCV Playing Card Detector", adaptée pour un usage Raspberry Pi.
"""

import cv2
import numpy as np
import os

# ----------------------------------------------------------------------
# PARAMÈTRES
# ----------------------------------------------------------------------

CARD_WIDTH = 200          # largeur de la carte "à plat" après warp
CARD_HEIGHT = 300         # hauteur de la carte "à plat" après warp


CORNER_WIDTH = 32         # largeur de la zone de coin extraite
CORNER_HEIGHT = 84        # hauteur de la zone de coin extraite

RANK_WIDTH = 70           # taille normalisée du symbole de rang
RANK_HEIGHT = 125

SUIT_WIDTH = 70           # taille normalisée du symbole de couleur
SUIT_HEIGHT = 100

BKG_THRESH = 60           # seuil pour distinguer fond / carte
CARD_THRESH = 30          # seuil pour isoler le texte du coin

MIN_CARD_AREA = 5000      # aire minimale (en pixels) pour considérer un contour comme une carte

RANKS = ["Ace", "2", "3", "4", "5", "6", "7", "8", "9", "10", "Jack", "Queen", "King"]
SUITS = ["Spades", "Hearts", "Clubs", "Diamonds"]  # Pique, Coeur, Trèfle, Carreau

REF_RANK_DIR = "references/ranks"
REF_SUIT_DIR = "references/suits"


# ----------------------------------------------------------------------
# ÉTAPE 1 : PRÉTRAITEMENT
# ----------------------------------------------------------------------

def preprocess_image(image):
    """Convertit en gris, floute, et seuille pour isoler les objets clairs sur fond sombre (ou l'inverse)."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    # Seuil adaptatif basé sur la luminosité moyenne du fond (coin de l'image)
    img_h, img_w = gray.shape
    bkg_level = gray[int(img_h / 100)][int(img_w / 2)]
    thresh_level = bkg_level + BKG_THRESH

    _, thresh = cv2.threshold(blur, thresh_level, 255, cv2.THRESH_BINARY)
    return thresh


# ----------------------------------------------------------------------
# ÉTAPE 2 : DÉTECTION DU CONTOUR DE LA CARTE
# ----------------------------------------------------------------------

def find_card_contour(thresh_image):
    """Trouve le plus grand contour à 4 côtés dans l'image seuillée."""
    contours, _ = cv2.findContours(thresh_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None

    # Trie par aire décroissante
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < MIN_CARD_AREA:
            break  # les suivants seront encore plus petits

        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)

        if len(approx) == 4:
            return approx.reshape(4, 2)

    return None


# ----------------------------------------------------------------------
# ÉTAPE 3 : CORRECTION DE PERSPECTIVE (WARP)
# ----------------------------------------------------------------------

def order_points(pts):
    """Ordonne 4 points : haut-gauche, haut-droite, bas-droite, bas-gauche."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]        # haut-gauche : somme minimale
    rect[2] = pts[np.argmax(s)]        # bas-droite : somme maximale

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]     # haut-droite
    rect[3] = pts[np.argmax(diff)]     # bas-gauche
    return rect


def flatten_card(image, points):
    """Applique une transformation de perspective pour obtenir une vue "à plat" de la carte."""
    rect = order_points(points.astype("float32"))

    dst = np.array([
        [0, 0],
        [CARD_WIDTH - 1, 0],
        [CARD_WIDTH - 1, CARD_HEIGHT - 1],
        [0, CARD_HEIGHT - 1]
    ], dtype="float32")

    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (CARD_WIDTH, CARD_HEIGHT))
    return warped


# ----------------------------------------------------------------------
# ÉTAPE 4 : EXTRACTION DU COIN (RANG + COULEUR)
# ----------------------------------------------------------------------

def extract_corner(warped_card):
    """Extrait la zone du coin haut-gauche contenant le rang et le symbole."""
    corner = warped_card[0:CORNER_HEIGHT, 0:CORNER_WIDTH]
    corner_zoom = cv2.resize(corner, (0, 0), fx=4, fy=4)

    gray = cv2.cvtColor(corner_zoom, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    # Seuillage adaptatif basé sur le niveau du fond du coin (souvent blanc)
    white_level = gray[15, int((CORNER_WIDTH * 4) / 2)]
    thresh_level = white_level - CARD_THRESH
    if thresh_level <= 0:
        thresh_level = 1

    _, thresh = cv2.threshold(blur, thresh_level, 255, cv2.THRESH_BINARY_INV)

    # Le rang est en haut, la couleur juste en dessous
    rank_region = thresh[20:185, 0:128]
    suit_region = thresh[186:336, 0:128]

    rank_final = isolate_symbol(rank_region, RANK_WIDTH, RANK_HEIGHT)
    suit_final = isolate_symbol(suit_region, SUIT_WIDTH, SUIT_HEIGHT)

    return rank_final, suit_final


def isolate_symbol(region, target_w, target_h):
    """Trouve le contour du symbole dans la région et le recadre/redimensionne proprement."""
    contours, _ = cv2.findContours(region, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None

    biggest = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(biggest)
    roi = region[y:y + h, x:x + w]
    resized = cv2.resize(roi, (target_w, target_h))
    return resized


# ----------------------------------------------------------------------
# ÉTAPE 5 : COMPARAISON AUX RÉFÉRENCES
# ----------------------------------------------------------------------

def load_references():
    """Charge les images de référence pour chaque rang et chaque couleur."""
    rank_refs = {}
    suit_refs = {}

    for rank in RANKS:
        path = os.path.join(REF_RANK_DIR, f"{rank}.jpg")
        if os.path.exists(path):
            rank_refs[rank] = cv2.imread(path, cv2.IMREAD_GRAYSCALE)

    for suit in SUITS:
        path = os.path.join(REF_SUIT_DIR, f"{suit}.jpg")
        if os.path.exists(path):
            suit_refs[suit] = cv2.imread(path, cv2.IMREAD_GRAYSCALE)

    return rank_refs, suit_refs


def match_symbol(candidate, references):
    """Compare l'image candidate à chaque référence et renvoie le meilleur match (score le plus faible = meilleur)."""
    if candidate is None:
        return "Unknown", float("inf")

    best_match = "Unknown"
    best_score = float("inf")

    for name, ref_image in references.items():
        diff = cv2.absdiff(candidate, ref_image)
        score = int(np.sum(diff) / 255)

        if score < best_score:
            best_score = score
            best_match = name

    return best_match, best_score


# ----------------------------------------------------------------------
# PIPELINE COMPLET
# ----------------------------------------------------------------------

def identify_card(image, rank_refs, suit_refs):
    """Prend une image (frame caméra), renvoie (rang, couleur) ou None si aucune carte détectée."""
    thresh = preprocess_image(image)
    contour = find_card_contour(thresh)

    if contour is None:
        return None

    warped = flatten_card(image, contour)
    rank_img, suit_img = extract_corner(warped)

    rank, rank_score = match_symbol(rank_img, rank_refs)
    suit, suit_score = match_symbol(suit_img, suit_refs)

    return {
        "rank": rank,
        "suit": suit,
        "rank_score": rank_score,
        "suit_score": suit_score,
        "warped_card": warped,
    }


# ----------------------------------------------------------------------
# EXEMPLE D'UTILISATION AVEC LA CAMÉRA DU RASPBERRY PI
# ----------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    import cv2

    from camera import Camera
    from video_preview import VideoPreview, build_preview_frame, detect_card_in_frame

    rank_refs, suit_refs = load_references()

    if not rank_refs or not suit_refs:
        print("Aucune reference trouvee dans 'references/ranks' et 'references/suits'.")
        print("Lance d'abord : python generate_references.py")

    use_web = "--web" in sys.argv
    preview = VideoPreview(use_web=use_web)
    cam = Camera()

    print("Detection en direct — Q pour quitter.")
    if use_web:
        print("Ouvre l'URL affichee dans ton navigateur.")

    try:
        while True:
            frame = cam.capture()
            if frame is None:
                continue

            detected = detect_card_in_frame(frame)
            title = "Reconnaissance carte"
            hints = "Q=quitter"

            if detected and rank_refs and suit_refs:
                result = identify_card(frame, rank_refs, suit_refs)
                if result:
                    title = f"{result['rank']} de {result['suit']}"
                    hints = f"scores {result['rank_score']}/{result['suit_score']}  |  Q=quitter"
                    print(f"Carte : {result['rank']} de {result['suit']} "
                          f"(scores: {result['rank_score']}, {result['suit_score']})")

            view = build_preview_frame(frame, detected, title=title, hints=hints)
            preview.show(view)

            if preview.use_gui and (cv2.waitKey(1) & 0xFF) == ord("q"):
                break
    finally:
        cam.cleanup()
        preview.close()
