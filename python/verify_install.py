#!/usr/bin/env python3
"""Verifie que Python, SSL, OpenCV (et MediaPipe si present) fonctionnent."""

from __future__ import annotations

import sys


def check(name: str, fn) -> bool:
    try:
        detail = fn()
    except Exception as exc:  # noqa: BLE001 - rapport d'install, on veut tout attraper
        print(f"[ECHEC] {name}: {exc}")
        return False
    print(f"[OK]    {name}: {detail}")
    return True


def ssl_ok() -> str:
    import ssl

    return ssl.OPENSSL_VERSION


def opencv_ok() -> str:
    import cv2

    return f"cv2 {cv2.__version__}"


def numpy_ok() -> str:
    import numpy as np

    return f"numpy {np.__version__}"


def mediapipe_ok() -> str:
    import mediapipe as mp

    version = getattr(mp, "__version__", "inconnu")
    return f"mediapipe {version}"


def main() -> int:
    print(f"Python {sys.version}")
    print(f"executable {sys.executable}")
    results = [
        check("ssl", ssl_ok),
        check("numpy", numpy_ok),
        check("opencv", opencv_ok),
    ]
    mediapipe_present = check("mediapipe (optionnel)", mediapipe_ok)
    if not mediapipe_present:
        print("MediaPipe est optionnel: OpenCV suffit pour reconnaitre des cartes.")

    if not all(results):
        print("\nInstallation incomplete. Relance scripts/install-opencv-rpi5.sh")
        return 1
    print("\nEnvironnement pret pour la reconnaissance de cartes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
