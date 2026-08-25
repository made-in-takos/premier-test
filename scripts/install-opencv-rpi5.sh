#!/usr/bin/env bash
# Installe OpenCV (et MediaPipe) sur Raspberry Pi 5 64-bit
# sans compiler Python a la main — c'est ce qui casse le module SSL.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-$ROOT/.venv}"
INSTALL_MEDIAPIPE="${INSTALL_MEDIAPIPE:-1}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

log() { printf '\n==> %s\n' "$*"; }
die() { printf 'ERREUR: %s\n' "$*" >&2; exit 1; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "commande introuvable: $1"
}

os_id() {
  . /etc/os-release
  printf '%s' "${VERSION_CODENAME:-unknown}"
}

python_ssl_ok() {
  "$1" -c "import ssl" >/dev/null 2>&1
}

log "Verification de la machine"
need_cmd uname
ARCH="$(uname -m)"
CODENAME="$(os_id)"
printf 'architecture=%s  os=%s\n' "$ARCH" "$CODENAME"

if [[ "$ARCH" != "aarch64" && "$ARCH" != "x86_64" ]]; then
  die "OS 32-bit ($ARCH) detecte. OpenCV/MediaPipe n'ont pas de wheels fiables.
Installe Raspberry Pi OS 64-bit (Bookworm ou Trixie) puis relance ce script."
fi

if [[ "$ARCH" != "aarch64" ]]; then
  printf 'Attention: ce script vise un Raspberry Pi 5 (aarch64). Architecture actuelle: %s\n' "$ARCH"
fi

log "Paquets systeme (dont libssl-dev, indispensable si un Python custom existe deja)"
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    python3 \
    python3-venv \
    python3-pip \
    python3-dev \
    python3-numpy \
    python3-opencv \
    python3-picamera2 \
    python3-gpiozero \
    python3-lgpio \
    build-essential \
    pkg-config \
    libssl-dev \
    libffi-dev \
    zlib1g-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libopenjp2-7 \
    libatlas-base-dev \
    libcamera-dev \
    libgl1 \
    libglib2.0-0
else
  printf 'apt-get absent: on continue avec pip uniquement.\n'
fi

need_cmd "$PYTHON_BIN"
PY_VER="$("$PYTHON_BIN" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
printf 'interprete=%s  version=%s\n' "$PYTHON_BIN" "$PY_VER"

if ! python_ssl_ok "$PYTHON_BIN"; then
  die "Le module ssl est absent de $PYTHON_BIN.
Tu as probablement compile Python 3.11 depuis les sources SANS libssl-dev.

Ne recompile pas tout de suite. Deux options:
  1) (recommandee) utilise le Python systeme: PYTHON_BIN=python3 $0
  2) reconstruis Python 3.11 AVEC SSL:  bash $ROOT/scripts/rebuild-python311-ssl.sh

Tant que ssl manque, pip ne peut pas telecharger OpenCV (HTTPS)."
fi

log "Environnement virtuel dans $VENV_DIR"
# --system-site-packages : picamera2 et python3-opencv (apt) restent visibles.
if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv --system-site-packages "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip setuptools wheel

log "Installation OpenCV via pip (wheels precompilees, pas de compilation locale)"
# Preferer un wheel. Si pip se met a compiler, on arrete tout de suite.
python -m pip install --only-binary=:all: "opencv-contrib-python>=4.10,<5" "numpy>=1.26,<3" \
  || python -m pip install "opencv-contrib-python>=4.10,<5" "numpy>=1.26,<3"

if [[ "$INSTALL_MEDIAPIPE" == "1" ]]; then
  log "Installation MediaPipe"
  # 1.0.x = nouveau SDK, wheel py3-none aarch64 (Python 3.13 OK).
  # 0.10.x = ancien SDK, wheels cp39-cp312 seulement (echec sur 3.13).
  if python -m pip install --only-binary=:all: "mediapipe>=1.0.1"; then
    printf 'MediaPipe 1.x installe.\n'
  else
    printf 'MediaPipe 1.x indisponible. Tentative 0.10.x (Python <= 3.12 uniquement)...\n'
    if python -m pip install "mediapipe>=0.10.14,<0.10.20"; then
      printf 'MediaPipe 0.10.x installe.\n'
    else
      printf 'MediaPipe n a pas pu etre installe. OpenCV suffit pour reconnaitre des cartes.\n'
      printf 'Relance avec INSTALL_MEDIAPIPE=0 pour ignorer ce module.\n'
    fi
  fi
fi

log "Verification"
python "$ROOT/vision/verify_install.py"

printf '\nOK. Active l environnement avec:\n  source %s/bin/activate\n' "$VENV_DIR"
printf 'Puis lance:\n  python vision/detect_cards.py --camera 0\n'
