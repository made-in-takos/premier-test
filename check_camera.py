#!/usr/bin/env python3
"""Diagnostic caméra — lance ce script en cas de problème."""

import glob
import platform
import subprocess
import sys

print("=== Diagnostic caméra ===\n")
print(f"Système   : {platform.system()} {platform.machine()}")

try:
    import config
    print(f"Pi détecté : {config.IS_RASPBERRY}")
except ImportError:
    print("config.py introuvable — lance depuis le dossier Carte/")
    sys.exit(1)

print(f"\nPériphériques vidéo : {glob.glob('/dev/video*') or '(aucun)'}")

print("\n--- Test picamera2 ---")
try:
    from picamera2 import Picamera2
    picam = Picamera2()
    picam.configure(picam.create_preview_configuration(main={"size": (640, 480)}))
    picam.start()
    frame = picam.capture_array()
    picam.stop()
    print(f"OK — frame {frame.shape[1]}x{frame.shape[0]}")
except ImportError:
    print("ÉCHEC — module absent : sudo apt install python3-picamera2")
except Exception as exc:
    print(f"ÉCHEC — {exc}")
    print("  → sudo raspi-config → Interface Options → Camera → Enable")
    print("  → sudo reboot")

print("\n--- Test OpenCV /dev/video* ---")
try:
    import cv2
    for dev in glob.glob("/dev/video*"):
        idx = dev.replace("/dev/video", "")
        try:
            idx = int(idx)
        except ValueError:
            continue
        cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
        if not cap.isOpened():
            cap = cv2.VideoCapture(idx)
        ok = cap.isOpened()
        if ok:
            ret, frame = cap.read()
            ok = ret and frame is not None
        cap.release()
        status = "OK" if ok else "échec"
        print(f"  video{idx} : {status}")
except ImportError:
    print("OpenCV non installé")

print("\n--- libcamera (si disponible) ---")
try:
    out = subprocess.run(
        ["libcamera-hello", "--list-cameras"],
        capture_output=True, text=True, timeout=10,
    )
    print(out.stdout or out.stderr or "(pas de sortie)")
except FileNotFoundError:
    print("libcamera-hello absent (normal sur PC)")
except subprocess.TimeoutExpired:
    print("Timeout")

print("\n=== Fin diagnostic ===")
