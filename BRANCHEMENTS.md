# Branchements — Trieur de cartes Raspberry Pi

Document de câblage pour le projet **Carte**  
Compte GitHub : [made-in-takos/Carte](https://github.com/made-in-takos/Carte)

Toutes les broches sont en numérotation **BCM** (Broadcom), pas BOARD.

---

## Vue d'ensemble du système

```
┌─────────────────────────────────────────────────────────────────┐
│                        RASPBERRY PI                              │
│                                                                  │
│  GPIO ──► Driver moteur pas-à-pas ──► Rotation bras (-90°/+90°) │
│  GPIO ──► Servo ──► Inclinaison bras (prise carte)              │
│  GPIO ──► 4 relais ──► 2 pompes + 2 électrovanne                │
│  GPIO ──► Pavé 4×4 + LCD 16×2 ──► Menus (jeu, tri, nombre)      │
│  CSI  ──► Camera Module Pi ──► Reconnaissance OpenCV            │
│  GPIO ──► Capteur point zéro ──► Homing rotation                │
└─────────────────────────────────────────────────────────────────┘
```

| Composant | Rôle |
|-----------|------|
| Moteur pas-à-pas | Rotation horizontale du bras |
| Servomoteur | Inclinaison du bras (descendre / relever la ventouse) |
| Circuit 1 (Pompe 1 + EV 1) | Aspiration et libération de la carte |
| Circuit 2 (Pompe 2 + EV 2) | Monter / descendre le vérin d'un étage |
| Pavé 4×4 | Menus : type de jeu, mode de tri, nombre de cartes |
| LCD 16×2 | Affichage des menus (HD44780, 4 bits) |
| Capteur point zéro | Référence mécanique à 0° |
| Caméra Pi | Identification des cartes |

---

## Tableau des broches GPIO

| GPIO (BCM) | Fonction | Connecté à |
|------------|----------|------------|
| **17** | STEP | Driver moteur pas-à-pas (impulsion pas) |
| **27** | DIR | Driver moteur pas-à-pas (direction) |
| **22** | ENABLE | Driver moteur pas-à-pas (actif bas) |
| **23** | HOME | Capteur point zéro (contact → GND) |
| **18** | SERVO | Signal PWM servomoteur (fil orange/jaune) |
| **24** | RELAIS 1 | Pompe 1 — circuit ventouse carte |
| **25** | RELAIS 2 | Électrovanne 1 — circuit ventouse carte |
| **5** | RELAIS 3 | Pompe 2 — circuit vérin vertical |
| **6** | RELAIS 4 | Électrovanne 2 — circuit vérin vertical |
| **7** | LCD RS | Afficheur HD44780 (Register Select) |
| **8** | LCD E | Afficheur HD44780 (Enable) |
| **9–11, 16** | LCD D4–D7 | Afficheur HD44780 data (4 bits) |
| **12, 13, 19, 26** | KEYPAD ROWS | Lignes du pavé 4×4 |
| **20, 21, 4, 15** | KEYPAD COLS | Colonnes du pavé 4×4 |

Broches communes :
- **5V** → servomoteur et LCD (broche VCC / LED A via résistance)
- **GND** → masse commune (Pi, driver, relais, capteur, LCD RW, pavé)

> Les numéros GPIO sont définis dans `config.py` et peuvent être modifiés si ton câblage diffère.

---

## 1. Moteur pas-à-pas (rotation du bras)

### Matériel
- Moteur pas-à-pas (ex. NEMA 17)
- Driver : A4988, DRV8825 ou TMC2208
- Alimentation moteur : **12 V externe** (selon moteur)
- Capteur point zéro : micro-switch ou capteur à effet Hall

### Schéma

```
Raspberry Pi                 Driver (A4988 / DRV8825)          Moteur NEMA 17
─────────────                ────────────────────────          ──────────────
GPIO 17 (STEP)  ───────────► STEP
GPIO 27 (DIR)   ───────────► DIR
GPIO 22 (EN)    ───────────► ENABLE (actif bas = moteur actif)
GND             ───────────► GND ◄──── GND alim 12V
                             VMOT ◄─── +12V (alim externe)
                             1A, 1B, 2A, 2B ────────────────► bobines moteur

GPIO 23 (HOME)  ◄─── contact capteur zéro ───► GND
                     (contact NO : fermé quand le bras est au zéro)
```

### Réglages driver
- **Micro-pas** : doit correspondre à `MICROSTEPS` dans `config.py` (défaut : 16)
- **Courant** : ajuster le potentiomètre du driver (NEMA 17 ≈ 0,8–1,2 A)
- **ENABLE actif bas** : GPIO 22 à LOW = moteur alimenté

### Capteur point zéro
- Câblage : une patte du switch sur **GPIO 23**, l'autre sur **GND**
- Le Pi utilise une résistance de pull-up interne
- Le switch est **normalement ouvert (NO)** : il ferme vers GND quand le bras atteint le zéro

---

## 2. Servomoteur (inclinaison du bras)

### Schéma

```
Raspberry Pi              Servomoteur (ex. SG90 / MG996R)
─────────────             ──────────────────────────────
GPIO 18 (signal) ───────► Fil signal (orange/jaune)
5V ─────────────────────► Fil + (rouge)  ← alim externe si gros servo
GND ────────────────────► Fil - (marron/noir)
```

### Calibration
Ajuster dans `config.py` :
- `SERVO_ANGLE_UP = 90` → bras relevé (transport)
- `SERVO_ANGLE_DOWN = 25` → bras baissé (contact carte)

Test :
```bash
python test_hardware.py servo-calibrate
```

---

## 3. Module relais (4 canaux)

### Principe
La plupart des modules relais 5 V pour Pi sont **actifs bas** : le relais s'active quand le GPIO est à **LOW**.

Paramètre dans `config.py` : `RELAY_ACTIVE_LOW = True`

### Schéma module relais

```
Raspberry Pi              Module relais 4 canaux
─────────────             ──────────────────────
GPIO 24 ─────────────────► IN1  → COM/NO → Pompe 1 (carte)
GPIO 25 ─────────────────► IN2  → COM/NO → Électrovanne 1 (carte)
GPIO 5  ─────────────────► IN3  → COM/NO → Pompe 2 (vérin)
GPIO 6  ─────────────────► IN4  → COM/NO → Électrovanne 2 (vérin)
5V ──────────────────────► VCC
GND ─────────────────────► GND
```

> **Ne jamais** alimenter pompes ou vérin depuis les broches 5V du Pi.  
> Les relais coupent / établissent un circuit alimenté **séparément** (12 V ou 24 V selon ton pneumatique).

---

## 4. Circuit 1 — Ventouse carte (Pompe 1 + EV 1)

### Rôle
- **Aspiration** : saisir une carte avec la ventouse
- **Libération** : relâcher la carte (pompe et vanne coupées)

### Séquence logicielle

| Action | Pompe 1 | EV 1 |
|--------|---------|------|
| Aspiration (`pick`) | ON | ON |
| Libération (`release`) | OFF | OFF |

### Schéma pneumatique simplifié

```
Pompe 1 ──► EV 1 ──► Ventouse (sur le bras)
              │
              └── (couper pompe + vanne = libération carte)
```

Test :
```bash
python test_hardware.py card-pick
python test_hardware.py card-release
```

---

## 5. Circuit 2 — Vérin vertical (Pompe 2 + EV 2)

### Rôle
Monter ou descendre le bras d'**un étage** (hauteur verticale), indépendamment de l'inclinaison servo.

### Séquence logicielle (par défaut)

| Action | Pompe 2 | EV 2 |
|--------|---------|------|
| Descendre (`down`) | ON | ON (pendant `LIFT_DOWN_HOLD_S`) |
| Monter (`up`) | OFF | OFF (remontée passive) |

Si ton vérin nécessite une **montée active**, configure dans `config.py` :
```python
LIFT_UP_PUMP_ON = True
LIFT_UP_VALVE_ON = True
LIFT_UP_HOLD_S = 2.0
```

Test :
```bash
python test_hardware.py lift-down
python test_hardware.py lift-up
```

---

## 6. Caméra Raspberry Pi

### Branchement
- **Camera Module** (CSI) : ruban dans le port CSI du Pi  
  - Pi 4 : contacts vers le port HDMI  
  - Pi 5 : vérifier le bon port CSI (deux ports disponibles)
- Pas de GPIO nécessaire

### Vérification
```bash
rpicam-hello --list-cameras
python check_camera.py
```

---

## 7. Alimentation — règles de sécurité

```
┌──────────────────┬────────────────────────────────────────────┐
│ Composant        │ Alimentation                               │
├──────────────────┼────────────────────────────────────────────┤
│ Raspberry Pi     │ 5 V (USB-C officiel, ≥ 3 A pour Pi 4)     │
│ Moteur pas-à-pas │ 12 V externe → driver                      │
│ Servomoteur      │ 5 V (Pi ou alim externe dédiée)            │
│ Module relais    │ 5 V (broche VCC du module)                 │
│ Pompes           │ Selon fiche technique (souvent 12 V)       │
│ Vérin            │ Via pompe hydraulique/pneumatique externe  │
└──────────────────┴────────────────────────────────────────────┘
```

**Obligatoire :**
1. Relier toutes les **masses (GND)** entre elles : Pi, driver, relais, alims externe
2. Ne pas tirer le moteur pas-à-pas depuis le 5 V du Pi
3. Couper l'alimentation avant tout recâblage
4. Utiliser des diodes de roue libre si le driver ne les intègre pas

---

## 8. Cycle complet — enchaînement mécanique

```
1. Homing rotation (capteur zéro) + vérin en haut + servo relevé
2. Rotation → position prise (PICKUP_ANGLE)
3. Vérin descend (circuit 2)
4. Servo incline vers le bas
5. Aspiration ventouse (circuit 1)
6. Servo remonte + vérin remonte
7. Rotation → caméra (0°) → reconnaissance OpenCV
8. Rotation → bac de tri (selon couleur)
9. Vérin descend + servo incline + libération ventouse
10. Servo remonte + vérin remonte + retour zéro
```

---

## 9. Ordre de test recommandé

```bash
cd ~/Carte
source venv/bin/activate

python test_hardware.py status      # vérifier config GPIO
python test_hardware.py pins        # clignotement relais + capteur zéro
python test_hardware.py step --steps 200 --dir cw   # moteur pas-à-pas
python test_hardware.py home        # homing
python test_hardware.py servo-calibrate             # angles servo
python test_hardware.py card-pick                   # ventouse
python test_hardware.py lift-down                   # vérin
python test_hardware.py pick-cycle                  # cycle mécanique complet
python test_hardware.py lcd                         # message LCD 16×2
python test_hardware.py keypad                      # lecture du pavé
python main.py                                      # menus LCD puis tri
```

---

## 10. Pavé numérique 4×4

Même disposition que le sketch Arduino (`Keypad.h`) :

```
1 2 3 A
4 5 6 B
7 8 9 C
* 0 # D
```

Les lignes sont des sorties (actives à LOW), les colonnes des entrées avec pull-up interne.

```
Raspberry Pi                    Pavé 4×4
─────────────                   ────────
GPIO 12 ──────────────────────► Ligne 1   (Arduino Mega 50)
GPIO 13 ──────────────────────► Ligne 2   (Arduino Mega 48)
GPIO 19 ──────────────────────► Ligne 3   (Arduino Mega 46)
GPIO 26 ──────────────────────► Ligne 4   (Arduino Mega 44)
GPIO 20 ──────────────────────► Colonne 1 (Arduino Mega 42)
GPIO 21 ──────────────────────► Colonne 2 (Arduino Mega 40)
GPIO 4  ──────────────────────► Colonne 3 (Arduino Mega 38)
GPIO 15 ──────────────────────► Colonne 4 (Arduino Mega 36)
```

GPIO 15 est aussi RXD de l'UART. Désactive le login série :

```bash
sudo raspi-config
# Interface Options → Serial Port → login shell : No
```

| Touche | Action |
|--------|--------|
| `0–9` | Chiffre / choix de menu |
| `#` | Valider |
| `*` | Effacer / revenir |
| `1 / 2 / 4 / 5 / 7 / 8` | Jog stepper ±1° / ±5° / ±20° (mise à zéro) |

---

## 11. Afficheur LCD 16×2 (HD44780, 4 bits)

Équivalent de `LiquidCrystal lcd(22, 24, 26, 28, 30, 32)` : RS, E, D4, D5, D6, D7. **RW à GND**.

```
Raspberry Pi              LCD 16×2
─────────────             ────────
GPIO 7  ────────────────► RS     (Arduino Mega 22)
GPIO 8  ────────────────► E      (Arduino Mega 24)
GPIO 9  ────────────────► D4     (Arduino Mega 26)
GPIO 10 ────────────────► D5     (Arduino Mega 28)
GPIO 11 ────────────────► D6     (Arduino Mega 30)
GPIO 16 ────────────────► D7     (Arduino Mega 32)
GND     ────────────────► RW, VSS, K (rétroéclairage −)
5V      ────────────────► VDD
5V (via 220 Ω) ─────────► A (rétroéclairage +)
Potard 10 kΩ   ─────────► VO (contraste), entre 5V et GND
```

Les numéros Mega ne se branchent pas tels quels sur le Pi : utilise le tableau BCM ci-dessus, ou modifie `config.py`.

---

## 12. Dépannage rapide

| Problème | Piste |
|----------|-------|
| Moteur ne tourne pas | Vérifier ENABLE (GPIO 22), alim 12 V driver, courant driver |
| Sens de rotation inversé | `DIR_INVERT = True` dans `config.py` |
| Homing timeout | Câblage capteur GPIO 23, ou `HOME_SEARCH_CLOCKWISE` |
| Relais ne switchent pas | `RELAY_ACTIVE_LOW`, alim 5 V module relais |
| Servo tremble | Alim externe 5 V dédiée, pas depuis le Pi |
| Caméra absente | `rpicam-hello --list-cameras`, ruban CSI |
| Ventouse ne prend pas | Timings `VACUUM_ON_DELAY_S`, fuite pneumatique |
| LCD illisible | Contraste VO, RW à GND, 5 V VDD, broches `LCD_*` |
| Pavé muet | Lignes/colonnes inversées, désactiver la console série (GPIO 15) |

---

## Fichiers liés

| Fichier | Contenu |
|---------|---------|
| `config.py` | Broches GPIO, angles, timings, LCD / pavé |
| `keypad.py` | Pavé 4×4 (gpiozero) |
| `lcd_display.py` | LCD HD44780 16×2 4 bits |
| `menu.py` | Menus type de jeu / tri / nombre de cartes |
| `sort_tables.py` | Angles Magic (18°) + Jeu 52 + Pokémon |
| `arm_controller.py` | Moteur pas-à-pas + homing |
| `servo_controller.py` | Inclinaison bras |
| `pneumatic.py` | Ventouse + vérin (4 relais) |
| `test_hardware.py` | Tests composant par composant |
| `main.py` | Menus + cycle automatique |

---

*Dernière mise à jour : correspond à la configuration du dépôt `made-in-takos/Carte`.*
