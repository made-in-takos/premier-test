"""
Servomoteur d'inclinaison — meme course que l'Arduino (40 a 130°).
"""

from __future__ import annotations

import time

import config
from gpio_setup import configure_pin_factory
from servo_math import clamp_servo_angle, servo_sweep


class ServoController:
    def __init__(self):
        configure_pin_factory()
        self._servo = None
        self._current_angle = clamp_servo_angle(
            config.SERVO_ANGLE_UP, config.SERVO_MIN_ANGLE, config.SERVO_MAX_ANGLE
        )

        if config.IS_RASPBERRY:
            from gpiozero import AngularServo

            # min/max 0–180 : write(n) = n degres, comme Servo.h Arduino.
            self._servo = AngularServo(
                config.GPIO_SERVO_TILT,
                min_angle=0,
                max_angle=180,
                min_pulse_width=config.SERVO_MIN_PULSE_US / 1_000_000,
                max_pulse_width=config.SERVO_MAX_PULSE_US / 1_000_000,
            )
            self._servo.angle = self._current_angle
        else:
            print("[SIMULATION] Servomoteur inclinaison")

    def move_to(self, angle, wait=True):
        target = clamp_servo_angle(angle, config.SERVO_MIN_ANGLE, config.SERVO_MAX_ANGLE)
        start = clamp_servo_angle(
            self._current_angle, config.SERVO_MIN_ANGLE, config.SERVO_MAX_ANGLE
        )
        for step_angle in servo_sweep(start, target):
            if self._servo:
                self._servo.angle = step_angle
            else:
                print(f"  [SIM] Servo → {step_angle}°")
            time.sleep(config.SERVO_STEP_DELAY_S)
            self._current_angle = step_angle
        if wait:
            time.sleep(config.SERVO_SETTLE_S)

    def up(self):
        print("  Servo : bras releve")
        self.move_to(config.SERVO_ANGLE_UP)

    def down(self):
        print("  Servo : bras baisse")
        self.move_to(config.SERVO_ANGLE_DOWN)

    @property
    def current_angle(self):
        return self._current_angle

    def cleanup(self):
        if self._servo:
            self.up()
            self._servo.close()
