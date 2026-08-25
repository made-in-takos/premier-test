"""
Servomoteur d'inclinaison — même usage que le sketch Arduino.

    ControlHauteurBras.write(50)

Pilotage identique au stepper qui fonctionne : gpiozero DigitalOutputDevice.
"""

import threading
import time

import config
from gpio_out import describe, digital_output

# Servo.h (Arduino)
_MIN_PULSE_US = 544
_MAX_PULSE_US = 2400
_REFRESH_US = 20_000


def _angle_to_pulse_us(angle):
    angle = max(0, min(180, int(angle)))
    return _MIN_PULSE_US + (angle / 180.0) * (_MAX_PULSE_US - _MIN_PULSE_US)


class ServoController:
    def __init__(self):
        self._angle = config.SERVO_ANGLE_DOWN
        self._pulse_us = _angle_to_pulse_us(self._angle)
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._pin = None

        if config.IS_RASPBERRY:
            self._attach()
            self.write(self._angle)
        else:
            print("[SIMULATION] Servo (comme Servo.write)")

    def write(self, angle):
        """Équivalent de ControlHauteurBras.write(angle)."""
        angle = max(0, min(180, int(round(angle))))
        with self._lock:
            self._angle = angle
            self._pulse_us = _angle_to_pulse_us(angle)

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
        print(f"  Servo : monter ({config.SERVO_ANGLE_UP}°)")
        self.move_to(config.SERVO_ANGLE_UP)

    def down(self):
        print(f"  Servo : descendre ({config.SERVO_ANGLE_DOWN}°)")
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
        self._pin = digital_output(bcm, initial_high=False)
        print(f"Servo signal → {describe(bcm)}  (à côté du stepper IN1, pin 11)")
        self._running = True
        self._thread = threading.Thread(target=self._refresh, daemon=True)
        self._thread.start()

    def _refresh(self):
        period_ns = _REFRESH_US * 1000
        pin = self._pin
        while self._running:
            with self._lock:
                pulse_ns = int(self._pulse_us * 1000)
            start = time.perf_counter_ns()
            pin.on()
            while time.perf_counter_ns() - start < pulse_ns:
                pass
            pin.off()
            rest = period_ns - (time.perf_counter_ns() - start)
            if rest > 2_000_000:
                time.sleep((rest - 400_000) / 1_000_000_000)
            while time.perf_counter_ns() - start < period_ns:
                pass

    def _detach(self):
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=0.5)
            self._thread = None
        if self._pin is not None:
            try:
                self._pin.off()
                self._pin.close()
            except Exception:
                pass
            self._pin = None
