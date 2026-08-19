"""
Contrôle du bras rotatif : 28BYJ-48 + shield ULN2003 (4 fils).

Séquence FULL4WIRE identique à AccelStepper (sketch Arduino) :
2048 pas / tour, soit ≈ 5,689 pas par degré.

Fonctionne sur Raspberry Pi avec gpiozero, ou en simulation sur PC.
"""

import time

import config

# 2 phases actives à la fois — AccelStepper::step4 / FULL4WIRE
# Ordre des bits : IN1, IN2, IN3, IN4 sur le ULN2003
FULL4WIRE_SEQUENCE = (
    (1, 1, 0, 0),
    (0, 1, 1, 0),
    (0, 0, 1, 1),
    (1, 0, 0, 1),
)


class ArmController:
    def __init__(self):
        self._current_angle = 0.0
        self._gpio = False
        self._coils = []
        self._home = None
        self._phase = 0
        self._dir_step = 1

        if config.IS_RASPBERRY:
            from gpiozero import DigitalOutputDevice, Button

            self._coils = [
                DigitalOutputDevice(pin, initial_value=False)
                for pin in config.GPIO_STEPPER_PINS
            ]
            self._home = Button(config.GPIO_HOME_SWITCH, pull_up=True, bounce_time=0.05)
            self._gpio = True
        else:
            print("[SIMULATION] Bras mécanique ULN2003 — pas de GPIO")

    def _angle_to_steps(self, angle):
        return int(round(angle * config.STEPS_PER_DEGREE))

    def _apply_phase(self):
        pattern = FULL4WIRE_SEQUENCE[self._phase % len(FULL4WIRE_SEQUENCE)]
        if self._gpio:
            for coil, bit in zip(self._coils, pattern):
                coil.on() if bit else coil.off()

    def _pulse_step(self, delay=None):
        delay = delay if delay is not None else config.STEP_DELAY_S
        self._phase = (self._phase + self._dir_step) % len(FULL4WIRE_SEQUENCE)
        self._apply_phase()
        time.sleep(delay)

    def _set_direction(self, clockwise):
        if config.DIR_INVERT:
            clockwise = not clockwise
        self._dir_step = 1 if clockwise else -1

    def enable_motor(self, enabled=True):
        """Alimente les bobines, ou les coupe (le 28BYJ-48 chauffe si on maintient)."""
        if enabled:
            self._apply_phase()
            return
        if self._gpio:
            for coil in self._coils:
                coil.off()

    def home(self):
        """Ramène le bras au point zéro via le capteur."""
        print("Homing…")
        self.enable_motor(True)
        self._set_direction(config.HOME_SEARCH_CLOCKWISE)

        if self._gpio:
            timeout = time.time() + 30.0
            while not self._home.is_pressed:
                self._pulse_step()
                if time.time() > timeout:
                    raise RuntimeError("Timeout homing — capteur zéro non détecté")

            if config.HOME_BACKOFF_DEG > 0:
                backoff_steps = self._angle_to_steps(config.HOME_BACKOFF_DEG)
                self._set_direction(not config.HOME_SEARCH_CLOCKWISE)
                for _ in range(backoff_steps):
                    self._pulse_step()
        else:
            time.sleep(0.5)
            print(f"[SIMULATION] Homing terminé à {config.HOME_ANGLE}°")

        self._current_angle = config.HOME_ANGLE
        self.enable_motor(False)
        print(f"Point zéro atteint ({self._current_angle}°)")

    def move_to(self, target_angle):
        """Déplace le bras à un angle cible (clampé entre MIN et MAX)."""
        target_angle = max(config.MIN_ANGLE, min(config.MAX_ANGLE, target_angle))
        delta = target_angle - self._current_angle
        if abs(delta) < 0.01:
            return

        steps = abs(self._angle_to_steps(delta))
        clockwise = delta > 0

        print(f"Déplacement {self._current_angle:.1f}° → {target_angle:.1f}° ({steps} pas)")
        self.enable_motor(True)
        self._set_direction(clockwise)

        for _ in range(steps):
            self._pulse_step()

        self.enable_motor(False)
        self._current_angle = target_angle

    def move_by(self, delta_deg):
        """Jog relatif (mise à zéro manuelle du sketch Arduino : +1° / -1° / +5°…)."""
        self.move_to(self._current_angle + delta_deg)

    def mark_as_zero(self):
        """Mémorise la position actuelle comme 0° (après réglage clavier)."""
        self._current_angle = config.HOME_ANGLE
        print(f"Position actuelle définie comme zéro ({self._current_angle}°)")

    @property
    def current_angle(self):
        return self._current_angle

    def cleanup(self):
        if self._gpio:
            self.enable_motor(False)
            for coil in self._coils:
                coil.close()
            self._coils = []
            if self._home is not None:
                self._home.close()
                self._home = None
            self._gpio = False
