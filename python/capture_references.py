#!/usr/bin/env python3
"""Enregistre une image de reference (rang ou couleur) a partir de la camera."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from camera import close_camera, open_camera, read_frame
from identify import RANKS, REF_RANK_DIR, REF_SUIT_DIR, SUITS, extract_corner, flatten_card, find_card_contour, preprocess_image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture des references rang/couleur")
    parser.add_argument("--rank", choices=RANKS, help="Nom du rang a enregistrer (Ace, 10, King, ...)")
    parser.add_argument("--suit", choices=SUITS, help="Nom de la couleur (Spades, Hearts, Clubs, Diamonds)")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--image", type=str, default="", help="Photo unique au lieu de la camera")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    import cv2

    if bool(args.rank) == bool(args.suit):
        print("Passe exactement une option: --rank Ace  OU  --suit Hearts", file=sys.stderr)
        return 1

    backend, cam = None, None
    if args.image:
        frame = cv2.imread(args.image)
        if frame is None:
            print(f"Impossible de lire {args.image}", file=sys.stderr)
            return 1
    else:
        opened = open_camera(args.camera)
        if opened is None:
            print("Aucune camera.", file=sys.stderr)
            return 1
        backend, cam = opened
        frame = read_frame(backend, cam)
        if frame is None:
            close_camera(backend, cam)
            print("Lecture camera impossible.", file=sys.stderr)
            return 1

    label = args.rank or args.suit
    dest_dir = REF_RANK_DIR if args.rank else REF_SUIT_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{label}.jpg"
    print("Espace = enregistrer, q = quitter. Montre UNE carte, coin haut-gauche lisible.")

    try:
        while True:
            thresh = preprocess_image(frame)
            contour = find_card_contour(thresh)
            preview = frame.copy()
            symbol = None
            if contour is not None:
                cv2.drawContours(preview, [contour.astype(int)], -1, (0, 255, 0), 2)
                warped = flatten_card(frame, contour)
                rank_img, suit_img = extract_corner(warped)
                symbol = rank_img if args.rank else suit_img
                cv2.imshow("carte a plat", warped)
                if symbol is not None:
                    cv2.imshow("symbole", symbol)
            cv2.putText(preview, f"cible: {label}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
            if args.image:
                if symbol is None:
                    print("Pas de symbole isole sur cette image.", file=sys.stderr)
                    return 1
                cv2.imwrite(str(dest), symbol)
                print(f"Sauve {dest}")
                return 0
            try:
                cv2.imshow("capture", preview)
                key = cv2.waitKey(1) & 0xFF
            except cv2.error as exc:
                print(f"Affichage indisponible ({exc}). Passe --image photo.jpg", file=sys.stderr)
                return 1
            if key in (ord("q"), 27):
                break
            if key == ord(" ") and symbol is not None:
                cv2.imwrite(str(dest), symbol)
                print(f"Sauve {dest}")
                break
            nxt = read_frame(backend, cam)
            if nxt is None:
                break
            frame = nxt
    finally:
        if backend is not None:
            close_camera(backend, cam)
        try:
            cv2.destroyAllWindows()
        except cv2.error:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
