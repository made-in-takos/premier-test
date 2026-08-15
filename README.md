# Reconnaissance de cartes — OpenCV sur Raspberry Pi 5

Ce dépôt installe **OpenCV** sur un Raspberry Pi 5 **64-bit** sans compiler Python à la main, puis détecte des cartes à jouer par contours.

MediaPipe n’est **pas nécessaire** pour reconnaître des cartes. Il sert surtout aux mains, au visage et à la pose.

## Pourquoi ça bloquait

Deux problèmes distincts, souvent mélangés :

1. **Python 3.13** (Raspberry Pi OS Trixie) : les anciennes versions de MediaPipe (`0.10.x`) n’ont des wheels que pour Python 3.9 à 3.12. `pip` refuse donc d’installer le module. OpenCV, lui, a des wheels 3.13.
2. **Python 3.11.16 compilé depuis les sources** : si `libssl-dev` n’était pas installé *avant* `./configure`, le module `_ssl` n’est pas construit. `pip` ne peut plus parler en HTTPS, donc OpenCV ne s’installe pas. Pointer `--with-openssl=/usr/bin/openssl` ne marche pas : c’est le binaire, pas le préfixe des headers.

La solution : **utiliser le Python du système** (3.11 sur Bookworm, 3.13 sur Trixie) dans un venv, et n’installer MediaPipe que dans sa version **1.0+** (wheel `py3-none` aussi pour `aarch64`).

## Prérequis

- Raspberry Pi 5 avec **Raspberry Pi OS 64-bit** (Bookworm ou Trixie)
- Caméra CSI (Picamera2) ou webcam USB
- Connexion Internet pour `apt` / `pip`

Vérifie l’architecture :

```bash
uname -m
```

Il faut `aarch64`. Un OS 32-bit (`armv7l`) n’a pas de wheels OpenCV / MediaPipe fiables.

## Installation (recommandée)

```bash
chmod +x scripts/install-opencv-rpi5.sh
bash scripts/install-opencv-rpi5.sh
source .venv/bin/activate
python python/verify_install.py
```

Le script :

- installe `libssl-dev` et les paquets système (`python3-opencv`, `python3-picamera2`, …)
- crée `.venv` avec `--system-site-packages` (la caméra CSI reste utilisable)
- installe OpenCV via un **wheel** précompilé (pas de compilation de 2 h sur le Pi)
- tente MediaPipe **>= 1.0.1** (compatible 3.13). Échec non bloquant.

Sans MediaPipe :

```bash
INSTALL_MEDIAPIPE=0 bash scripts/install-opencv-rpi5.sh
```

## Si tu as déjà compilé Python 3.11 sans SSL

N’essaie pas `pip install` avec cet interpréteur : HTTPS est mort.

Option A — rester sur le Python système (le plus simple) :

```bash
PYTHON_BIN=python3 bash scripts/install-opencv-rpi5.sh
```

Option B — reconstruire 3.11 **avec** SSL, puis relancer l’installeur :

```bash
chmod +x scripts/rebuild-python311-ssl.sh
bash scripts/rebuild-python311-ssl.sh
PYTHON_BIN=/usr/local/bin/python3.11 bash scripts/install-opencv-rpi5.sh
```

Le rebuild installe d’abord `libssl-dev`, fait `make distclean`, puis `./configure` **sans** `--with-openssl=/usr/bin/openssl`. `make altinstall` n’écrase pas `python3` du système.

## Lancer la détection

```bash
source .venv/bin/activate
python python/detect_cards.py --camera 0
```

Sans écran / en SSH :

```bash
python python/detect_cards.py --synthetic --no-window --save /tmp/carte.jpg
```

Sur une photo :

```bash
python python/detect_cards.py --image photo.jpg --save resultat.jpg
```

`q` ou `Échap` quitte la fenêtre.

## Tests (sans caméra)

```bash
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest tests
```

## Fichiers utiles

| Fichier | Rôle |
| --- | --- |
| `scripts/install-opencv-rpi5.sh` | Installation OpenCV / MediaPipe |
| `scripts/rebuild-python311-ssl.sh` | Reconstruction Python 3.11 avec SSL |
| `python/verify_install.py` | Contrôle ssl, OpenCV, MediaPipe |
| `python/card_geometry.py` | Contours aux proportions d’une carte |
| `python/detect_cards.py` | Aperçu caméra / image |
| `requirements.txt` | Dépendances Python |
