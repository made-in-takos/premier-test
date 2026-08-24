"""
Configuration globale du trieur de cartes.
Les angles servo et la polarite des relais suivent le sketch Arduino d'origine.
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
# GPIO — moteur pas-a-pas (rotation du bras)
# ---------------------------------------------------------------------------

GPIO_STEP = 17
GPIO_DIR = 27
GPIO_ENABLE = 22
GPIO_HOME_SWITCH = 23

# ---------------------------------------------------------------------------
# GPIO — Circuit 1 : ventouse carte (Pompe 1 + EV 1)
# ---------------------------------------------------------------------------

GPIO_RELAY_PUMP_CARD = 24
GPIO_RELAY_VALVE_CARD = 25

# ---------------------------------------------------------------------------
# GPIO — Circuit 2 : verin vertical / etage (Pompe 2 + EV 2)
# ---------------------------------------------------------------------------

GPIO_RELAY_PUMP_LIFT = 5
GPIO_RELAY_VALVE_LIFT = 6

# Arduino : digitalWrite HIGH = pompe ON. La vanne piston etait inversee
# (Allumer=true → LOW). Les modules "low level trigger" demandent True.
RELAY_ACTIVE_LOW = False
RELAY_INVERT_CHANNELS = ("valve_lift",)

# ---------------------------------------------------------------------------
# GPIO — servomoteur (inclinaison du bras)
# ---------------------------------------------------------------------------

GPIO_SERVO_TILT = 18

# Sketch Arduino : write(130) releve, write(50) baisse, 40 ms / degre.
# Course mecanique limitee a 40–130° (pas 0–180).
SERVO_ANGLE_UP = 130
SERVO_ANGLE_DOWN = 40
SERVO_MIN_ANGLE = 40
SERVO_MAX_ANGLE = 130
SERVO_STEP_DELAY_S = 0.04
SERVO_MIN_PULSE_US = 544
SERVO_MAX_PULSE_US = 2400
SERVO_SETTLE_S = 0.2

# ---------------------------------------------------------------------------
# Moteur pas-a-pas
# ---------------------------------------------------------------------------

STEPS_PER_REV = 200
MICROSTEPS = 16
GEAR_RATIO = 1.0
STEPS_PER_DEGREE = (STEPS_PER_REV * MICROSTEPS * GEAR_RATIO) / 360.0

MIN_ANGLE = -90.0
MAX_ANGLE = 90.0
HOME_ANGLE = 0.0

STEP_DELAY_S = 0.001
HOME_SEARCH_CLOCKWISE = False
HOME_BACKOFF_DEG = 2.0
DIR_INVERT = False

# ---------------------------------------------------------------------------
# Positions rotation (degres)
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
# Circuit 1 — ventouse
# ---------------------------------------------------------------------------

VACUUM_ON_DELAY_S = 0.5
VACUUM_OFF_DELAY_S = 0.3

# ---------------------------------------------------------------------------
# Circuit 2 — verin vertical
# ---------------------------------------------------------------------------

LIFT_DOWN_PUMP_ON = True
LIFT_DOWN_VALVE_ON = True
LIFT_UP_PUMP_ON = False
LIFT_UP_VALVE_ON = False
LIFT_DOWN_HOLD_S = 2.0
LIFT_UP_HOLD_S = 2.0
LIFT_SETTLE_S = 0.4

# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------

CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
CAMERA_INDEX = 0
CAMERA_BACKEND = "auto"

MAX_RANK_SCORE = 8000
MAX_SUIT_SCORE = 6000
MAX_IDENTIFY_ATTEMPTS = 5
