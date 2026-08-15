"""Acces camera: Picamera2 (CSI) puis webcam USB OpenCV."""

from __future__ import annotations


def open_camera(index: int = 0):
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
