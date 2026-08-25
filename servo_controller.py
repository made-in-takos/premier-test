"""
Servomoteur d'inclinaison — même usage que le sketch Arduino.

    ControlHauteurBras.write(50)

Le servo ne comprend PAS les degrés : il veut ~50 impulsions par seconde
dont la largeur (µs) code la position. write(angle) est l'échelle 0–180
de Servo.h (544–2400 µs).

lgpio.tx_pulse(on, off) n'est PAS cet API : sur le Pi 5 ça sort ~2,5 Hz
(tick-tick lent). On utilise tx_servo(largeur_µs), prévu pour ça.
"""

import time

import config
from gpio_out import claim_lgpio_output, describe

_REFRESH_US = 20_000
_REFRESH_HZ = 50
# Plage documentée de lgpio.tx_servo (0 = stop).
_SERVO_TX_MIN_US = 500
_SERVO_TX_MAX_US = 2500


def angle_to_pulse_us(angle):
    """Équivalent de Servo.write : 0–180 → min–max µs (Servo.h)."""
    lo = float(config.SERVO_MIN_PULSE_US)
    hi = float(config.SERVO_MAX_PULSE_US)
    angle = max(0, min(180, int(round(angle))))
    return lo + (angle / 180.0) * (hi - lo)


class ServoController:
    def __init__(self):
        self._angle = config.SERVO_ANGLE_DOWN
        self._lgpio = None
        self._handle = None
        self._gpio = None

        if config.IS_RASPBERRY:
            self._attach()
            self.write(self._angle)
        else:
            print("[SIMULATION] Servo (échelle 0–180 → impulsions µs, comme Servo.write)")

    def write(self, angle):
        """Équivalent de ControlHauteurBras.write(angle)."""
        angle = max(0, min(180, int(round(angle))))
        self._angle = angle
        if self._handle is not None:
            self._send_pulse(angle_to_pulse_us(angle))

    def move_to(self, angle, wait=True):
        """Équivalent de FCTControlleServo(cible, vitesse)."""
        target = max(0, min(180, int(round(angle))))
        speed = config.SERVO_SPEED_MS if wait else 0
        current = self._angle
        if speed > 0 and current != target:
            step = 1 if target > current else -1
            for value in range(current, target, step):
                self.write(value)
                time.sleep(speed / 1000.0)
        self.write(target)

    def up(self):
        pulse = angle_to_pulse_us(config.SERVO_ANGLE_UP)
        print(f"  Servo : monter  write({config.SERVO_ANGLE_UP}) = {pulse:.0f} µs")
        self.move_to(config.SERVO_ANGLE_UP)

    def down(self):
        pulse = angle_to_pulse_us(config.SERVO_ANGLE_DOWN)
        print(f"  Servo : descendre  write({config.SERVO_ANGLE_DOWN}) = {pulse:.0f} µs")
        self.move_to(config.SERVO_ANGLE_DOWN)

    @property
    def current_angle(self):
        return self._angle

    def cleanup(self, park=True):
        if park and config.IS_RASPBERRY:
            try:
                self.down()
            except Exception:
                pass
        self._detach()

    def _attach(self):
        bcm = config.GPIO_SERVO_TILT
        self._lgpio, self._handle, self._gpio = claim_lgpio_output(bcm)
        print(
            f"Servo {describe(bcm)}  —  tx_servo 50 Hz, "
            f"write(0)={config.SERVO_MIN_PULSE_US} µs, "
            f"write(180)={config.SERVO_MAX_PULSE_US} µs"
        )

    def _send_pulse(self, pulse_us):
        width = int(round(pulse_us))
        width = max(_SERVO_TX_MIN_US, min(_SERVO_TX_MAX_US, width))
        # 50 impulsions/s, largeur en µs — comme Servo.writeMicroseconds().
        if hasattr(self._lgpio, "tx_servo"):
            self._lgpio.tx_servo(self._handle, self._gpio, width)
            return
        duty = 100.0 * width / _REFRESH_US
        self._lgpio.tx_pwm(self._handle, self._gpio, float(_REFRESH_HZ), duty)

    def _stop_pwm(self):
        if self._handle is None or self._gpio is None or self._lgpio is None:
            return
        try:
            if hasattr(self._lgpio, "tx_servo"):
                self._lgpio.tx_servo(self._handle, self._gpio, 0)
            else:
                self._lgpio.tx_pwm(self._handle, self._gpio, 0, 0)
        except Exception:
            pass
        try:
            self._lgpio.gpio_free(self._handle, self._gpio)
        except Exception:
            pass

    def _detach(self):
        self._stop_pwm()
        self._handle = None
        self._gpio = None
        self._lgpio = None
