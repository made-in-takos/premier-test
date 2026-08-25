"""
Servomoteur d'inclinaison — même usage que le sketch Arduino.

    ControlHauteurBras.write(50)

Impulsions identiques à Servo.h : 544–2400 µs à 50 Hz.
Sur le Pi le PWM passe par gpiozero PWMOutputDevice (lgpio.tx_pwm),
pas par un on/off Python : ce bit-bang allongeait les impulsions,
d'où un bras trop lent et des angles faux.
"""

import time

import config
from gpio_out import describe

# Servo.h (Arduino)
_MIN_PULSE_US = 544
_MAX_PULSE_US = 2400
_REFRESH_US = 20_000
_REFRESH_HZ = 50


def angle_to_pulse_us(angle):
    """Équivalent de Servo.write : 0° → 544 µs, 180° → 2400 µs."""
    angle = max(0, min(180, int(round(angle))))
    return _MIN_PULSE_US + (angle / 180.0) * (_MAX_PULSE_US - _MIN_PULSE_US)


def _duty_cycle(angle):
    return angle_to_pulse_us(angle) / _REFRESH_US


class ServoController:
    def __init__(self):
        self._angle = config.SERVO_ANGLE_DOWN
        self._pwm = None

        if config.IS_RASPBERRY:
            self._attach()
            self.write(self._angle)
        else:
            print("[SIMULATION] Servo (comme Servo.write)")

    def write(self, angle):
        """Équivalent de ControlHauteurBras.write(angle)."""
        angle = max(0, min(180, int(round(angle))))
        self._angle = angle
        if self._pwm is not None:
            self._pwm.value = _duty_cycle(angle)

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
        print(f"  Servo : monter ({config.SERVO_ANGLE_UP}°)  {pulse:.0f} µs")
        self.move_to(config.SERVO_ANGLE_UP)

    def down(self):
        pulse = angle_to_pulse_us(config.SERVO_ANGLE_DOWN)
        print(f"  Servo : descendre ({config.SERVO_ANGLE_DOWN}°)  {pulse:.0f} µs")
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
        from gpiozero import PWMOutputDevice

        bcm = config.GPIO_SERVO_TILT
        rest = _duty_cycle(self._angle)
        self._pwm = PWMOutputDevice(
            bcm,
            frequency=_REFRESH_HZ,
            initial_value=rest,
        )
        print(
            f"Servo PWM {_REFRESH_HZ} Hz → {describe(bcm)}  "
            f"(544–2400 µs, comme Servo.h)"
        )

    def _detach(self):
        if self._pwm is None:
            return
        try:
            self._pwm.value = 0
            self._pwm.close()
        except Exception:
            pass
        self._pwm = None
