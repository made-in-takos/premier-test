"""
Capture d'images depuis la caméra Raspberry Pi (picamera2) ou webcam USB.
"""

import glob
import sys

import config


def _list_video_devices():
    return sorted(glob.glob("/dev/video*"))


def _try_picamera2():
    from picamera2 import Picamera2

    picam = Picamera2()
    picam.configure(
        picam.create_preview_configuration(
            main={"size": (config.CAMERA_WIDTH, config.CAMERA_HEIGHT)}
        )
    )
    picam.start()
    # Test de capture
    frame = picam.capture_array()
    if frame is None or frame.size == 0:
        picam.stop()
        raise RuntimeError("picamera2 : capture vide")
    return picam


def _try_opencv(index):
    import cv2

    # V4L2 direct — évite parfois les soucis GStreamer sur Pi OS
    cap = cv2.VideoCapture(index, cv2.CAP_V4L2)
    if not cap.isOpened():
        cap.release()
        cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        cap.release()
        return None

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)

    ok, frame = cap.read()
    if not ok or frame is None:
        cap.release()
        return None

    return cap


class Camera:
    def __init__(self):
        self._source = None
        self._mode = None
        self._opencv_index = None

        backend = config.CAMERA_BACKEND.lower()
        errors = []

        # --- picamera2 (Camera Module Pi) ---
        if backend in ("auto", "picamera2") and config.IS_RASPBERRY:
            try:
                self._source = _try_picamera2()
                self._mode = "picamera2"
            except ImportError:
                errors.append("picamera2 non installé → sudo apt install python3-picamera2")
            except Exception as exc:
                errors.append(f"picamera2 : {exc}")

        # --- OpenCV /dev/videoN (webcam USB) ---
        if self._mode is None and backend in ("auto", "opencv"):
            indices = [config.CAMERA_INDEX]
            if backend == "auto":
                indices.extend(i for i in range(4) if i != config.CAMERA_INDEX)

            for index in indices:
                cap = _try_opencv(index)
                if cap is not None:
                    self._source = cap
                    self._mode = "opencv"
                    self._opencv_index = index
                    break

            if self._mode is None:
                devices = _list_video_devices()
                if devices:
                    errors.append(f"OpenCV n'a ouvert aucun index, devices vus : {', '.join(devices)}")
                else:
                    errors.append("Aucun /dev/video* — caméra non détectée ou non activée")

        if self._mode is None:
            print("\n=== ERREUR CAMÉRA ===")
            for msg in errors:
                print(f"  • {msg}")
            print("\nVérifications :")
            print("  1. Camera Module Pi → sudo apt install python3-picamera2")
            print("  2. Activer la caméra → sudo raspi-config → Interface Options → Camera")
            print("  3. Webcam USB → brancher et tester : ls /dev/video*")
            print("  4. Redémarrer après activation → sudo reboot")
            print("  5. Diagnostic → python check_camera.py\n")
            sys.exit(1)

        detail = self._mode
        if self._mode == "opencv":
            detail += f" (/dev/video{self._opencv_index})"
        print(f"Caméra initialisée ({detail})")

    def capture(self):
        """Retourne une frame BGR (numpy) ou None en cas d'échec."""
        import cv2

        if self._mode == "picamera2":
            frame = self._source.capture_array()
            return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        ok, frame = self._source.read()
        return frame if ok else None

    def cleanup(self):
        if self._mode == "picamera2":
            self._source.stop()
        elif self._source is not None:
            self._source.release()
