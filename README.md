# Trieur de cartes — Raspberry Pi 5

Menus **pavé 4×4** + **LCD 16×2**, moteur **28BYJ-48 / ULN2003**, reconnaissance OpenCV (jeu de 52).

## Lancement

```bash
bash setup_pi.sh
source venv/bin/activate
python main.py
```

Sans menus :

```bash
python main.py --skip-menu --skip-test --deck playing --sort Color --count 52
```

## Menus

`#` valide, `*` efface.

1. Mise à zéro du bras (`1/2` ±1°, `4/5` ±5°, `7/8` ±20°)
2. Tests : `1` servo (monter/descendre ×2), `2` rotation, `3` relais
3. Type de cartes : `1:52  2:Pkm  3:Mag`
4. Mode de tri (selon le jeu)
5. Nombre de cartes

## Fichiers

| Fichier | Rôle |
| --- | --- |
| `main.py` | Menus + cycle de tri |
| `config.py` | Broches GPIO, angles, timings |
| `menu.py` / `keypad.py` / `lcd_display.py` | Interface utilisateur |
| `arm_controller.py` | Rotation ULN2003 |
| `servo_controller.py` | Inclinaison du bras |
| `pneumatic.py` | Ventouse + vérin |
| `card_recognition.py` | OpenCV (jeu 52) |
| `BRANCHEMENTS.md` | Câblage |

## Tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest tests
python test_hardware.py servo-sweep
python test_hardware.py lcd
python test_hardware.py keypad
```
