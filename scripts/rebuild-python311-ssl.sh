#!/usr/bin/env bash
# Reconstruit un Python 3.11 compile depuis les sources AVEC le module ssl.
# A n'utiliser que si tu tiens absolument a python3.11 custom.
# Preferer le Python systeme + scripts/install-opencv-rpi5.sh
set -euo pipefail

PYTHON_VERSION="${PYTHON_VERSION:-3.11.16}"
PREFIX="${PREFIX:-/usr/local}"
SRC_PARENT="${SRC_PARENT:-$HOME/src}"
JOBS="${JOBS:-$(nproc 2>/dev/null || echo 4)}"

log() { printf '\n==> %s\n' "$*"; }
die() { printf 'ERREUR: %s\n' "$*" >&2; exit 1; }

log "Dependances de compilation (libssl-dev = headers OpenSSL, pas le binaire openssl)"
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  build-essential \
  gdb \
  lcov \
  pkg-config \
  wget \
  libbz2-dev \
  libffi-dev \
  libgdbm-dev \
  libgdbm-compat-dev \
  liblzma-dev \
  libncurses5-dev \
  libreadline6-dev \
  libsqlite3-dev \
  libssl-dev \
  lzma \
  lzma-dev \
  tk-dev \
  uuid-dev \
  zlib1g-dev

if ! pkg-config --exists openssl; then
  die "pkg-config ne trouve pas openssl. Verifie que libssl-dev est installe."
fi
printf 'OpenSSL detecte: %s\n' "$(pkg-config --modversion openssl)"
printf 'Headers: %s\n' "$(pkg-config --cflags openssl)"

mkdir -p "$SRC_PARENT"
cd "$SRC_PARENT"

TARBALL="Python-${PYTHON_VERSION}.tgz"
if [[ ! -f "$TARBALL" ]]; then
  log "Telechargement de Python ${PYTHON_VERSION}"
  wget -O "$TARBALL" "https://www.python.org/ftp/python/${PYTHON_VERSION}/${TARBALL}"
fi

log "Extraction"
rm -rf "Python-${PYTHON_VERSION}"
tar xf "$TARBALL"
cd "Python-${PYTHON_VERSION}"

# make distclean est indispensable si une precedente compilation a ignore SSL.
if [[ -f Makefile ]]; then
  make distclean || true
fi

log "configure (ne PAS passer --with-openssl=/usr/bin/openssl : c'est le binaire, pas le prefix)"
./configure \
  --prefix="$PREFIX" \
  --enable-optimizations \
  --with-ensurepip=install \
  --with-openssl-rpath=auto

log "Compilation (-j${JOBS}). Sur Pi 5 cela prend plusieurs minutes."
make -j"$JOBS"

log "Installation sans ecraser python3 systeme (altinstall -> python3.11)"
sudo make altinstall

BIN="${PREFIX}/bin/python3.11"
"$BIN" -c "import ssl, sys; print('ssl OK', ssl.OPENSSL_VERSION, sys.version)"
"$BIN" -m pip --version

printf '\nPython 3.11 avec SSL pret: %s\n' "$BIN"
printf 'Ensuite:\n  PYTHON_BIN=%s bash %s/scripts/install-opencv-rpi5.sh\n' \
  "$BIN" "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
