#!/usr/bin/env python3
"""Apercu camera: encadre les cartes detectees. MediaPipe n'est pas requis."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from card_geometry import draw_candidates, find_card_candidates, synthetic_card_frame


def open_camera(index: int):
    try:
        from picamera2 import Picamera2  # type: ignore

        cam = Picamera2()
        cam.configure(cam.create_preview_configuration(main={"format": "RGB888", "size": (1280, 720)}))
        cam.start()
        return ("picamera2", cam)
    except Exception:
        import cv2

        cap = cv2.VideoCapture(index)
        if not cap.isOpened():
            return None
        return ("opencv", cap)


def read_frame(backend: str, cam):
    import cv2

    if backend == "picamera2":
        rgb = cam.capture_array()
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    ok, frame = cam.read()
    return frame if ok else None


def close_camera(backend: str, cam) -> None:
    if backend == "picamera2":
        cam.stop()
        return
    cam.release()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detection de cartes a jouer (OpenCV)")
    parser.add_argument("--camera", type=int, default=0, help="Index OpenCV si Picamera2 est absent")
    parser.add_argument("--image", type=str, default="", help="Chemin d'une image au lieu de la camera")
    parser.add_argument("--synthetic", action="store_true", help="Utilise une carte synthetique (sans camera)")
    parser.add_argument("--no-window", action="store_true", help="Pas d'affichage, utile en SSH")
    parser.add_argument("--save", type=str, default="", help="Enregistre le resultat")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    import cv2

    if args.synthetic:
        frame = synthetic_card_frame()
        backend, cam = None, None
    elif args.image:
        frame = cv2.imread(args.image)
        if frame is None:
            print(f"Impossible de lire {args.image}", file=sys.stderr)
            return 1
        backend, cam = None, None
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
            candidates = find_card_candidates(frame)
            output = draw_candidates(frame, candidates)
            print(f"{len(candidates)} carte(s) detectee(s)")
            if args.save:
                cv2.imwrite(args.save, output)
                print(f"Sauve: {args.save}")
            if args.no_window or args.synthetic or args.image:
                break
            try:
                cv2.imshow("cartes", output)
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
