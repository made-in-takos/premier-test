#!/usr/bin/env python3
"""Apercu camera : detecte et nomme la carte (OpenCV, sans MediaPipe)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from camera import close_camera, open_camera, read_frame
from card_geometry import synthetic_card_frame
from identify import identify_card, load_references


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reconnaissance de cartes a jouer (OpenCV)")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--image", type=str, default="")
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--no-window", action="store_true")
    parser.add_argument("--save", type=str, default="")
    parser.add_argument("--debug", action="store_true", help="Affiche la carte aplatie et le coin")
    return parser.parse_args()


def annotate(frame, result) -> object:
    import cv2

    output = frame.copy()
    if result is None:
        cv2.putText(output, "Aucune carte", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
        return output
    contour = result["contour"].astype(int)
    cv2.drawContours(output, [contour], -1, (0, 255, 0), 2)
    label = f"{result['rank']} de {result['suit']}  ({result['rank_score']:.0f}/{result['suit_score']:.0f})"
    color = (0, 255, 0) if result["rank"] != "Unknown" and result["suit"] != "Unknown" else (0, 255, 255)
    x, y = int(contour[:, 0].min()), int(contour[:, 1].min())
    cv2.putText(output, label, (x, max(30, y - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    return output


def show_debug(result) -> None:
    import cv2

    if result is None:
        return
    cv2.imshow("carte a plat", result["warped_card"])
    if result["rank_img"] is not None:
        cv2.imshow("rang", result["rank_img"])
    if result["suit_img"] is not None:
        cv2.imshow("couleur", result["suit_img"])


def main() -> int:
    args = parse_args()
    import cv2

    rank_refs, suit_refs = load_references()
    if not rank_refs or not suit_refs:
        print("Aucune reference dans references/ranks et references/suits.")
        print("Capture-les avec: python python/capture_references.py --rank Ace")
        print("La detection de contour fonctionne deja; le nommage attend les photos.")

    backend, cam = None, None
    if args.synthetic:
        frame = synthetic_card_frame()
    elif args.image:
        frame = cv2.imread(args.image)
        if frame is None:
            print(f"Impossible de lire {args.image}", file=sys.stderr)
            return 1
    else:
        opened = open_camera(args.camera)
        if opened is None:
            print("Aucune camera. Essaie --synthetic ou --image fichier.jpg", file=sys.stderr)
            return 1
        backend, cam = opened
        frame = read_frame(backend, cam)
        if frame is None:
            print("Lecture camera impossible.", file=sys.stderr)
            close_camera(backend, cam)
            return 1

    try:
        while True:
            result = identify_card(frame, rank_refs, suit_refs)
            output = annotate(frame, result)
            if result:
                print(
                    f"Carte: {result['rank']} de {result['suit']} "
                    f"(scores {result['rank_score']:.0f}, {result['suit_score']:.0f})"
                )
            else:
                print("Aucune carte")
            if args.save:
                cv2.imwrite(args.save, output)
                print(f"Sauve: {args.save}")
            if args.no_window or args.synthetic or args.image:
                break
            try:
                cv2.imshow("cartes", output)
                if args.debug:
                    show_debug(result)
                key = cv2.waitKey(1) & 0xFF
            except cv2.error as exc:
                print(f"Affichage OpenCV indisponible ({exc}). Utilise --no-window.", file=sys.stderr)
                break
            if key in (ord("q"), 27):
                break
            if backend is None:
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
