# Trieur de cartes — Raspberry Pi 5

Reconnaissance OpenCV + commande GPIO (servo 40–130°, relais, bras).

```
config.py          Broches GPIO et angles servo
vision/            Camera et identification des cartes
hardware/          Servo, relais, moteur pas-a-pas
scripts/           Installation et tests materiel
references/        Photos de rang / couleur
tests/             Tests sans camera
```

## Installation

```bash
uname -m    # aarch64
bash scripts/install-opencv-rpi5.sh
source .venv/bin/activate
python vision/verify_install.py
```

Utilise le Python systeme. Ne compile pas Python a la main (le module `ssl` casse sinon).

## Vision

```bash
python vision/capture_references.py --rank Ace
python vision/detect_cards.py --camera 0
python vision/detect_cards.py --image photo.jpg --save resultat.jpg --no-window
```

## Servo

Course Arduino : **40°** (baisse) a **130°** (releve), 40 ms par degre.

```bash
python scripts/test_hardware.py servo-sweep
```

Alim 5 V externe pour le servo, masses communes.

## Tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest tests
```
