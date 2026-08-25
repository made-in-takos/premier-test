"""
Controle du bras rotatif (moteur pas-a-pas + capteur zero).
"""

import time

import config
from hardware.gpio_setup import configure_pin_factory


class ArmController:
    def __init__(self):
        configure_pin_factory()
        self._current_angle = 0.0
        self._gpio = None
        self._step = self._dir = self._enable = self._home = None

        if config.IS_RASPBERRY:
            from gpiozero import DigitalOutputDevice, Button

            self._step = DigitalOutputDevice(config.GPIO_STEP, initial_value=False)
            self._dir = DigitalOutputDevice(config.GPIO_DIR, initial_value=False)
            self._enable = DigitalOutputDevice(config.GPIO_ENABLE, active_high=False, initial_value=False)
            self._home = Button(config.GPIO_HOME_SWITCH, pull_up=True, bounce_time=0.05)
            self._gpio = True
        else:
            print("[SIMULATION] Bras mecanique — pas de GPIO")

    def _angle_to_steps(self, angle):
        return int(round(angle * config.STEPS_PER_DEGREE))

    def _pulse_step(self, delay=None):
        delay = delay if delay is not None else config.STEP_DELAY_S
        if self._gpio:
            self._step.on()
            time.sleep(delay)
            self._step.off()
            time.sleep(delay)
        else:
            time.sleep(delay * 2)

    def _set_direction(self, clockwise):
        if config.DIR_INVERT:
            clockwise = not clockwise
        if self._gpio:
            self._dir.value = 1 if clockwise else 0

    def enable_motor(self, enabled=True):
        if self._gpio:
            self._enable.value = 0 if enabled else 1

    def home(self):
        print("Homing…")
        self.enable_motor(True)
        self._set_direction(config.HOME_SEARCH_CLOCKWISE)

        if self._gpio:
            timeout = time.time() + 30.0
            while not self._home.is_pressed:
                self._pulse_step()
                if time.time() > timeout:
                    raise RuntimeError("Timeout homing — capteur zero non detecte")

            if config.HOME_BACKOFF_DEG > 0:
                backoff_steps = self._angle_to_steps(config.HOME_BACKOFF_DEG)
                self._set_direction(not config.HOME_SEARCH_CLOCKWISE)
                for _ in range(backoff_steps):
                    self._pulse_step()
        else:
            time.sleep(0.5)
            print(f"[SIMULATION] Homing termine a {config.HOME_ANGLE}°")

        self._current_angle = config.HOME_ANGLE
        self.enable_motor(False)
        print(f"Point zero atteint ({self._current_angle}°)")

    def move_to(self, target_angle):
        target_angle = max(config.MIN_ANGLE, min(config.MAX_ANGLE, target_angle))
        delta = target_angle - self._current_angle
        if abs(delta) < 0.01:
            return

        steps = abs(self._angle_to_steps(delta))
        clockwise = delta > 0

        print(f"Deplacement {self._current_angle:.1f}° → {target_angle:.1f}° ({steps} pas)")
        self.enable_motor(True)
        self._set_direction(clockwise)

        for _ in range(steps):
            self._pulse_step()

        self.enable_motor(False)
        self._current_angle = target_angle

    @property
    def current_angle(self):
        return self._current_angle

    def cleanup(self):
        if self._gpio:
            self.enable_motor(False)
            for dev in (self._step, self._dir, self._enable):
                if dev is not None:
                    dev.close()
            if self._home is not None:
                self._home.close()
