# Reconnaissance de cartes — OpenCV sur Raspberry Pi 5

Le cœur du projet est le pipeline **contour → carte à plat → coin → références**, inspiré du tutoriel EdjeElectronics. MediaPipe n’est pas utilisé.

## Est-ce une bonne base ?

Oui. C’est l’approche classique et adaptée à un Pi 5 :

1. Seuillage pour isoler la carte (fond sombre)
2. Plus grand quadrilatère
3. `warpPerspective` vers 200×300
4. Zoom du coin haut-gauche (rang + couleur)
5. `absdiff` contre une photo de *ton* jeu

Ce n’est pas encore un classifieur neuronal : il faut **17 photos de référence** du même paquet, sous le même éclairage.

Points déjà corrigés par rapport au brouillon :

- `cv2.resize(roi, (w, h), 0, 0)` plantait (le 3e argument n’est pas `fx`)
- les références sont redimensionnées au chargement
- si la carte est à l’envers, on teste aussi la rotation 180°
- si le quadrilatère est en paysage, on tourne l’ordre des coins pour rester en portrait
- un score trop mauvais devient `Unknown` au lieu d’un faux nom

À caler ensuite sur le tapis réel : `BKG_THRESH`, découpe du coin, et le fond (tapis sombre, une carte à la fois, coin lisible).

## Installation OpenCV (Pi 5 64-bit)

```bash
uname -m    # doit afficher aarch64
bash scripts/install-opencv-rpi5.sh
source .venv/bin/activate
python python/verify_install.py
```

Détail SSL / Python 3.13 : voir plus bas. En résumé, **ne compile pas Python à la main** ; utilise le Python système.

## Capturer les références

Même jeu, lumière stable, fond sombre :

```bash
python python/capture_references.py --rank Ace
python python/capture_references.py --suit Hearts
```

Espace enregistre, `q` quitte. Fichiers attendus : `references/ranks/*.jpg` et `references/suits/*.jpg` (noms anglais : `Ace`, `10`, `King`, `Spades`, …).

## Reconnaître une carte

```bash
python python/detect_cards.py --camera 0
python python/detect_cards.py --camera 0 --debug
python python/detect_cards.py --image photo.jpg --save resultat.jpg --no-window
```

Picamera2 (CSI) est essayé en premier, sinon webcam USB.

## Servo (course Arduino 40–130°)

Le sketch Mega faisait `write(130)` (bras relevé) et s’arrêtait vers **40°**, à 40 ms par degré. Le Pi envoyait 25° et 90°. C’est recalé : `SERVO_ANGLE_DOWN = 40`, `SERVO_ANGLE_UP = 130`.

```bash
sudo apt install -y python3-gpiozero python3-lgpio
source .venv/bin/activate
python test_hardware.py servo-sweep
```

Alim **5 V externe** pour le servo (pas le 5 V du Pi), masses communes.

## Tests sans caméra

```bash
python -m pip install -r requirements-dev.txt
python -m pytest tests
```

## Pourquoi OpenCV ne s’installait pas

1. **Python 3.13** (Trixie) : MediaPipe `0.10.x` n’a pas de wheel. Inutile ici. OpenCV a des wheels 3.13. MediaPipe `1.0+` est optionnel.
2. **Python 3.11 compilé sans `libssl-dev`** : plus de module `ssl`, donc plus de `pip` HTTPS. Relancer `scripts/install-opencv-rpi5.sh` avec le Python système, ou `scripts/rebuild-python311-ssl.sh` seulement si tu tiens à un 3.11 custom.

## Fichiers

| Fichier | Rôle |
| --- | --- |
| `python/identify.py` | Pipeline rang/couleur |
| `python/detect_cards.py` | Boucle caméra |
| `python/capture_references.py` | Photos de référence |
| `python/camera.py` | Picamera2 / USB |
| `config.py` | Broches GPIO, servo 40–130° |
| `servo_controller.py` | Inclinaison (course Arduino) |
| `test_hardware.py` | `servo-sweep` et calibration |
| `scripts/install-opencv-rpi5.sh` | Installation OpenCV |
| `references/` | Templates du jeu |
