"""
Configuration globale du trieur de cartes.
Adapte les broches GPIO et les angles selon ton câblage réel.
"""

import platform


def _is_raspberry_pi():
    if platform.system() != "Linux":
        return False
    machine = platform.machine().lower()
    if machine.startswith("arm") or machine in ("aarch64", "arm64"):
        try:
            with open("/proc/device-tree/model", encoding="utf-8") as f:
                return "raspberry pi" in f.read().lower()
        except OSError:
            return True
    return False


IS_RASPBERRY = _is_raspberry_pi()

# ---------------------------------------------------------------------------
# GPIO — moteur pas-à-pas 28BYJ-48 + shield ULN2003 (4 fils)
# Arduino Mega : AccelStepper FULL4WIRE, pins 33, 29, 31, 27
#                (IN1, IN3, IN2, IN4 dans l'ordre AccelStepper)
# ---------------------------------------------------------------------------

GPIO_STEPPER_IN1 = 17
GPIO_STEPPER_IN2 = 27
GPIO_STEPPER_IN3 = 22
GPIO_STEPPER_IN4 = 14  # UART TX — désactiver le login série
GPIO_STEPPER_PINS = (
    GPIO_STEPPER_IN1,
    GPIO_STEPPER_IN2,
    GPIO_STEPPER_IN3,
    GPIO_STEPPER_IN4,
)
GPIO_HOME_SWITCH = 23

# ---------------------------------------------------------------------------
# GPIO — Circuit 1 : ventouse carte (Pompe 1 + EV 1)
# ---------------------------------------------------------------------------

GPIO_RELAY_PUMP_CARD = 24
GPIO_RELAY_VALVE_CARD = 25

# ---------------------------------------------------------------------------
# GPIO — Circuit 2 : vérin vertical / étage (Pompe 2 + EV 2)
# ---------------------------------------------------------------------------

GPIO_RELAY_PUMP_LIFT = 5
GPIO_RELAY_VALVE_LIFT = 6

RELAY_ACTIVE_LOW = True

# ---------------------------------------------------------------------------
# GPIO — servomoteur (inclinaison du bras)
# ---------------------------------------------------------------------------

# Repos = position basse. Identique au sketch Arduino (50 = relevé, 130 = baissé).
SERVO_ANGLE_UP = 50
SERVO_ANGLE_DOWN = 130
SERVO_INVERT = False  # True si le bras se lève dans le mauvais sens

GPIO_SERVO_TILT = 18  # pin physique 12 — signal 3,3 V

# Impulsions type SG90 / MG90S (50 Hz). 1500 µs ≈ 90°.
SERVO_MIN_PULSE_US = 500
SERVO_MAX_PULSE_US = 2500
SERVO_PWM_HZ = 50
SERVO_SETTLE_S = 0.6
# Balayage progressif (comme FCTControlleServo sur l'Arduino). 0 = saut direct.
SERVO_MS_PER_DEG = 15
# auto = impulsions busy-wait (fiable sur Pi 5). Autres : lgpio, thread.
SERVO_BACKEND = "auto"

# ---------------------------------------------------------------------------
# Moteur pas-à-pas 28BYJ-48 (réducteur 64:1) + ULN2003
# AccelStepper FULL4WIRE : 2048 pas / tour  →  2048/360 ≈ 5,689 pas/°
# ---------------------------------------------------------------------------

STEPS_PER_REV = 2048
STEPS_PER_DEGREE = STEPS_PER_REV / 360.0  # identique à degre * 5.689 sur l'Arduino

# Étendu à ±180° pour le tri Magic (pas de 18°, comme sur l'Arduino).
MIN_ANGLE = -180.0
MAX_ANGLE = 180.0
HOME_ANGLE = 0.0

# ~500 pas/s max, comme BaseRotation.setMaxSpeed(500) sur l'Arduino
STEP_DELAY_S = 0.002
HOME_SEARCH_CLOCKWISE = False
HOME_BACKOFF_DEG = 2.0
DIR_INVERT = False

# ---------------------------------------------------------------------------
# Positions rotation (degrés)
# ---------------------------------------------------------------------------

PICKUP_ANGLE = -45.0
CAMERA_ANGLE = 0.0

SORT_ANGLES = {
    "Hearts": -75.0,
    "Diamonds": -50.0,
    "Clubs": 50.0,
    "Spades": 75.0,
}

# ---------------------------------------------------------------------------
# Circuit 1 — ventouse (aspiration + libération)
# ---------------------------------------------------------------------------

VACUUM_ON_DELAY_S = 0.5
VACUUM_OFF_DELAY_S = 0.3

# ---------------------------------------------------------------------------
# Circuit 2 — vérin vertical (monter / descendre un étage)
# ---------------------------------------------------------------------------

# États relais pour DESCENDRE d'un étage (ON = relais actif)
LIFT_DOWN_PUMP_ON = True
LIFT_DOWN_VALVE_ON = True

# États relais pour MONTER d'un étage
# Si le vérin remonte seul (ressort/gravité) : laisse False / False
LIFT_UP_PUMP_ON = False
LIFT_UP_VALVE_ON = False

LIFT_DOWN_HOLD_S = 2.0    # durée descente d'un étage
LIFT_UP_HOLD_S = 2.0        # durée montée active (0 si remontée passive)
LIFT_SETTLE_S = 0.4         # stabilisation après mouvement

# ---------------------------------------------------------------------------
# Caméra
# ---------------------------------------------------------------------------

CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
CAMERA_INDEX = 0
CAMERA_BACKEND = "auto"

MAX_RANK_SCORE = 8000
MAX_SUIT_SCORE = 6000
MAX_IDENTIFY_ATTEMPTS = 5

# ---------------------------------------------------------------------------
# GPIO — pavé numérique 4×4 (même disposition que l'Arduino)
# {'1','2','3','A'}
# {'4','5','6','B'}
# {'7','8','9','C'}
# {'*','0','#','D'}
#
# Arduino Mega : lignes 50,48,46,44  /  colonnes 42,40,38,36
# ---------------------------------------------------------------------------

KEYPAD_ROW_PINS = [12, 13, 19, 26]
KEYPAD_COL_PINS = [20, 21, 4, 15]
KEYPAD_DEBOUNCE_S = 0.05

# ---------------------------------------------------------------------------
# GPIO — afficheur LCD 16×2 en 4 bits (HD44780, RW à GND)
# Arduino : LiquidCrystal lcd(22, 24, 26, 28, 30, 32)
#           → RS, E, D4, D5, D6, D7
# ---------------------------------------------------------------------------

LCD_RS = 7
LCD_E = 8
LCD_DATA_PINS = [9, 10, 11, 16]  # D4, D5, D6, D7
LCD_COLS = 16
LCD_ROWS = 2

# Délais d'affichage (calqués sur delay(1500) / delay(2000) de l'Arduino)
LCD_MESSAGE_DELAY_S = 1.5
LCD_CONFIRM_DELAY_S = 2.0
HARDWARE_TEST_HOLD_S = 2.0

# ---------------------------------------------------------------------------
# Menus — types de jeu et modes de tri
# ---------------------------------------------------------------------------

DECK_PLAYING = "playing"
DECK_POKEMON = "pokemon"
DECK_MAGIC = "magic"

DEFAULT_DECK = DECK_MAGIC
DEFAULT_SORT_MODE = "Color"
MAX_CARD_COUNT = 999

# Pas d'angle du tri Magic (FCTTriParCouleur)
MAGIC_ANGLE_STEP = 18
