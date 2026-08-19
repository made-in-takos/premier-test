#!/usr/bin/env python3
"""Aperçu caméra simple avec détection de carte en direct."""

import argparse
import sys

import cv2

from camera import Camera
from card_recognition import identify_card, load_references
from video_preview import VideoPreview, build_preview_frame, detect_card_in_frame


def main():
    parser = argparse.ArgumentParser(description="Aperçu caméra + détection carte")
    parser.add_argument("--web", action="store_true", help="Flux dans le navigateur")
    parser.add_argument("--identify", action="store_true", help="Afficher rang/couleur reconnus")
    args = parser.parse_args()

    rank_refs, suit_refs = {}, {}
    if args.identify:
        rank_refs, suit_refs = load_references()
        if not rank_refs or not suit_refs:
            print("Références manquantes — lance generate_references.py d'abord.")
            sys.exit(1)

    preview = VideoPreview(use_web=args.web)
    cam = Camera()

    print("Aperçu actif — Q pour quitter.")

    try:
        while True:
            frame = cam.capture()
            if frame is None:
                continue

            detected = detect_card_in_frame(frame)
            title = "Apercu camera"
            hints = "Q=quitter"

            if detected and args.identify:
                result = identify_card(frame, rank_refs, suit_refs)
                if result:
                    title = f"{result['rank']} de {result['suit']}"
                    hints = f"scores {result['rank_score']}/{result['suit_score']}  |  Q=quitter"

            view = build_preview_frame(frame, detected, title=title, hints=hints)
            preview.show(view)

            if preview.use_gui and (cv2.waitKey(1) & 0xFF) in (ord("q"), ord("Q")):
                break
    finally:
        cam.cleanup()
        preview.close()


if __name__ == "__main__":
    main()
