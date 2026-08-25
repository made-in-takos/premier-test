#!/bin/bash
# Installation recommandée sur Raspberry Pi OS (Bookworm+)
set -e

echo "=== Paquets système (apt) ==="
sudo apt update
sudo apt install -y \
    python3-venv \
    python3-full \
    python3-opencv \
    python3-numpy \
    python3-gpiozero \
    python3-lgpio \
    python3-picamera2 \
    libatlas-base-dev

echo "=== Environnement virtuel ==="
python3 -m venv venv --system-site-packages

echo "=== Activation + pip ==="
# shellcheck disable=SC1091
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "=== Terminé ==="
echo "Pour lancer le projet :"
echo "  source venv/bin/activate"
echo "  python main.py"
echo ""
echo "Si le pavé (GPIO 15) ou le ULN2003 IN4 (GPIO 14) : désactive le login série"
echo "  (raspi-config → Interface Options → Serial Port → login shell No)"
