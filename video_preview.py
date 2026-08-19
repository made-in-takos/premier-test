"""
Affichage du flux vidéo avec overlay de détection.
Fenêtre OpenCV locale, ou flux web (--web) si tu es connecté en SSH.
"""

import os
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2
import numpy as np

from card_recognition import (
    extract_corner,
    find_card_contour,
    flatten_card,
    preprocess_image,
)

WINDOW_NAME = "Carte - flux video"
WEB_PORT = 8080

_latest_jpeg = None
_jpeg_lock = threading.Lock()
_web_server = None


def setup_display():
    """Vérifie que l'affichage graphique est disponible."""
    display = os.environ.get("DISPLAY")
    if display:
        return True

    print("\n⚠️  Variable DISPLAY non définie — la fenêtre OpenCV ne s'affichera pas.")
    print("   Si un écran est branché sur le Pi, lance :")
    print("       export DISPLAY=:0")
    print("       python generate_references.py")
    print("   Si tu es en SSH sans écran, utilise le flux web :")
    print("       python generate_references.py --web")
    print("       puis ouvre http://<IP-du-Pi>:8080 dans ton navigateur\n")
    return False


def detect_card_in_frame(frame):
    """Détecte une carte et extrait rang + couleur."""
    thresh = preprocess_image(frame)
    contour = find_card_contour(thresh)
    if contour is None:
        return None

    warped = flatten_card(frame, contour)
    rank_img, suit_img = extract_corner(warped)
    if rank_img is None or suit_img is None:
        return None

    display = frame.copy()
    cv2.polylines(display, [contour.astype(int)], True, (0, 255, 0), 2)

    return {
        "rank_img": rank_img,
        "suit_img": suit_img,
        "warped": warped,
        "display": display,
        "contour": contour,
    }


def build_preview_frame(frame, detected=None, title="", hints="ESPACE=capturer  S=passer  Q=quitter"):
    """Construit l'image affichée : caméra + carte aplatie + symboles."""
    if detected is None:
        view = frame.copy()
        color = (0, 0, 255)
        status = "Place la carte devant la camera"
    else:
        view = detected["display"].copy()
        color = (0, 255, 0)
        status = "Carte detectee [OK]"

    cv2.putText(view, title, (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
    cv2.putText(view, status, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)
    cv2.putText(view, hints, (10, view.shape[0] - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1)

    if detected is None:
        return view

    warped = cv2.resize(detected["warped"], (200, 300))
    rank_view = cv2.cvtColor(detected["rank_img"], cv2.COLOR_GRAY2BGR)
    suit_view = cv2.cvtColor(detected["suit_img"], cv2.COLOR_GRAY2BGR)
    rank_view = cv2.resize(rank_view, (120, 200))
    suit_view = cv2.resize(suit_view, (120, 160))

    side = np.zeros((max(warped.shape[0], rank_view.shape[0] + suit_view.shape[0] + 10), 220, 3), dtype=np.uint8)
    side[: warped.shape[0], :200] = warped
    y = warped.shape[0] + 5
    if y + rank_view.shape[0] <= side.shape[0]:
        side[y : y + rank_view.shape[0], :120] = rank_view
        side[y : y + suit_view.shape[0], 125:245] = suit_view

    h = max(view.shape[0], side.shape[0])
    canvas = np.zeros((h, view.shape[1] + side.shape[1] + 10, 3), dtype=np.uint8)
    canvas[: view.shape[0], : view.shape[1]] = view
    canvas[: side.shape[0], view.shape[1] + 10 :] = side[:, : canvas.shape[1] - view.shape[1] - 10]
    return canvas


def _encode_jpeg(frame):
    ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    return buf.tobytes() if ok else None


def _update_web_frame(frame):
    global _latest_jpeg
    data = _encode_jpeg(frame)
    if data:
        with _jpeg_lock:
            _latest_jpeg = data


class _MjpegHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<!DOCTYPE html><html><head><meta charset='utf-8'>"
                b"<title>Carte - flux video</title>"
                b"<style>body{margin:0;background:#111;display:flex;justify-content:center;"
                b"align-items:center;min-height:100vh}img{max-width:100%;max-height:100vh}</style>"
                b"</head><body><img src='/stream'></body></html>"
            )
            return

        if self.path != "/stream":
            self.send_error(404)
            return

        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()

        while True:
            with _jpeg_lock:
                frame = _latest_jpeg
            if frame:
                try:
                    self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n\r\n")
                    self.wfile.write(frame)
                    self.wfile.write(b"\r\n")
                except (BrokenPipeError, ConnectionResetError):
                    break
            time.sleep(0.033)


def start_web_stream(port=WEB_PORT):
    """Démarre un serveur MJPEG accessible dans le navigateur."""
    global _web_server

    def _run():
        global _web_server
        _web_server = ThreadingHTTPServer(("0.0.0.0", port), _MjpegHandler)
        _web_server.serve_forever()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    hostname = socket.gethostname()
    try:
        ip = socket.gethostbyname(hostname)
    except OSError:
        ip = "127.0.0.1"

    print(f"\n📷 Flux web actif : http://{ip}:{port}")
    print(f"   (ou http://localhost:{port} si tu es sur le Pi)\n")


def stop_web_stream():
    global _web_server
    if _web_server:
        _web_server.shutdown()
        _web_server = None


class VideoPreview:
    """Affiche le flux caméra en fenêtre et/ou dans le navigateur."""

    def __init__(self, use_gui=True, use_web=False, web_port=WEB_PORT):
        self.use_gui = use_gui and setup_display()
        self.use_web = use_web

        if self.use_gui:
            cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(WINDOW_NAME, 1280, 720)

        if self.use_web:
            start_web_stream(web_port)

    def show(self, frame):
        if self.use_web:
            _update_web_frame(frame)
        if self.use_gui:
            cv2.imshow(WINDOW_NAME, frame)

    def close(self):
        stop_web_stream()
        if self.use_gui:
            cv2.destroyAllWindows()
