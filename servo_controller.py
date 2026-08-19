"""
Contrôle du servomoteur d'inclinaison du bras.
"""

import time

import config


class ServoController:
    def __init__(self):
        self._servo = None
        self._current_angle = config.SERVO_ANGLE_UP

        if config.IS_RASPBERRY:
            from gpiozero import AngularServo

            self._servo = AngularServo(
                config.GPIO_SERVO_TILT,
                min_angle=0,
                max_angle=180,
                min_pulse_width=config.SERVO_MIN_PULSE_US / 1_000_000,
                max_pulse_width=config.SERVO_MAX_PULSE_US / 1_000_000,
            )
            self._servo.angle = config.SERVO_ANGLE_UP
        else:
            print("[SIMULATION] Servomoteur inclinaison")

    def move_to(self, angle, wait=True):
        angle = max(0, min(180, angle))
        if self._servo:
            self._servo.angle = angle
        else:
            print(f"  [SIM] Servo → {angle}°")
        self._current_angle = angle
        if wait:
            time.sleep(config.SERVO_SETTLE_S)

    def up(self):
        """Bras relevé — position transport."""
        print("  Servo : bras relevé")
        self.move_to(config.SERVO_ANGLE_UP)

    def down(self):
        """Bras baissé — prise ou dépôt de carte."""
        print("  Servo : bras baissé")
        self.move_to(config.SERVO_ANGLE_DOWN)

    @property
    def current_angle(self):
        return self._current_angle

    def cleanup(self):
        if self._servo:
            self.up()
            self._servo.close()
