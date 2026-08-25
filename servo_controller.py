"""
Servomoteur d'inclinaison — même usage que le sketch Arduino.

    ControlHauteurBras.write(50)

Le servo ne comprend PAS les degrés. Il mesure la largeur d'impulsion (µs)
à 50 Hz. write(angle) est une échelle logicielle 0–180, identique à Servo.h :

    0°   → SERVO_MIN_PULSE_US  (544 µs par défaut)
    180° → SERVO_MAX_PULSE_US  (2400 µs)

Sur un SG90, 1000–2000 µs ≈ 0–180° mécaniques. Donc write(50) Arduino
envoie ~1060 µs (~10° mécaniques), pas un vrai 50°.

Les impulsions partent en microsecondes (lgpio), pas en % PWM gpiozero
(1 % = 200 µs ≈ 20° d'erreur).
"""

import time

import config
from gpio_out import describe, digital_output

_REFRESH_US = 20_000
_REFRESH_HZ = 50


def angle_to_pulse_us(angle):
    """Équivalent de Servo.write : 0–180 → min–max µs (Servo.h)."""
    lo = float(config.SERVO_MIN_PULSE_US)
    hi = float(config.SERVO_MAX_PULSE_US)
    angle = max(0, min(180, int(round(angle))))
    return lo + (angle / 180.0) * (hi - lo)


class ServoController:
    def __init__(self):
        self._angle = config.SERVO_ANGLE_DOWN
        self._dev = None
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
        import lgpio

        bcm = config.GPIO_SERVO_TILT
        self._dev = digital_output(bcm, initial_high=False)
        factory = self._dev.pin_factory
        self._handle = getattr(factory, "_handle", None)
        self._gpio = bcm
        if self._handle is None:
            self._dev.close()
            self._dev = None
            raise RuntimeError(
                "Servo : gpiozero n'a pas de handle lgpio "
                "(même driver que le stepper attendu sur Pi 5)."
            )
        self._lgpio = lgpio
        print(
            f"Servo {describe(bcm)}  —  "
            f"write(0)={config.SERVO_MIN_PULSE_US} µs, "
            f"write(180)={config.SERVO_MAX_PULSE_US} µs  "
            f"(le servo lit des µs, pas des degrés)"
        )

    def _send_pulse(self, pulse_us):
        on_us = int(round(pulse_us))
        on_us = max(1, min(_REFRESH_US - 1, on_us))
        off_us = _REFRESH_US - on_us
        # Largeur d'impulsion en µs, comme Servo.writeMicroseconds().
        self._lgpio.tx_pulse(self._handle, self._gpio, on_us, off_us)

    def _detach(self):
        if self._handle is not None and self._gpio is not None:
            try:
                self._lgpio.tx_pulse(self._handle, self._gpio, 0, 0)
            except Exception:
                try:
                    self._lgpio.tx_pwm(self._handle, self._gpio, 0, 0)
                except Exception:
                    pass
        self._handle = None
        self._gpio = None
        if self._dev is not None:
            try:
                self._dev.off()
                self._dev.close()
            except Exception:
                pass
            self._dev = None
