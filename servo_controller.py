"""
Servomoteur d'inclinaison — même usage que le sketch Arduino.

    ControlHauteurBras.write(50)

Le servo veut 50 impulsions/s (toutes les 20 ms). Sur le Pi 5, le timer
logiciel lgpio (tx_pulse / tx_pwm / tx_servo) sort ~2,5 Hz : tick-tick
et un cran de temps en temps. On génère le 50 Hz nous-mêmes avec
lgpio.gpio_write — le même appel que le stepper qui marche.
"""

import threading
import time

import config
from gpio_out import claim_lgpio_output, describe

_REFRESH_US = 20_000
_REFRESH_HZ = 50


def angle_to_pulse_us(angle):
    """0° → MIN µs, 180° → MAX µs (linéaire)."""
    lo = float(config.SERVO_MIN_PULSE_US)
    hi = float(config.SERVO_MAX_PULSE_US)
    angle = max(0, min(180, int(round(angle))))
    return lo + (angle / 180.0) * (hi - lo)


def command_pulse_us(angle):
    """Impulsion réellement envoyée (inversion + trim)."""
    angle = max(0, min(180, int(round(angle))))
    if config.SERVO_INVERT:
        angle = 180 - angle
    return angle_to_pulse_us(angle) + float(config.SERVO_PULSE_TRIM_US)


class _GpioWritePwm:
    """PWM 50 Hz par gpio_write. N'utilise pas le timer lgpio (cassé sur Pi 5)."""

    def __init__(self, lgpio_mod, handle, gpio, pulse_us):
        self._lgpio = lgpio_mod
        self._handle = handle
        self._gpio = gpio
        self._pulse_us = float(pulse_us)
        self._off_comp_ns = self._median_write_ns()
        self._lock = threading.Lock()
        self._running = True
        self.measured_hz = 0.0
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="servo-pwm-50hz"
        )
        self._thread.start()

    def set_pulse_us(self, pulse_us):
        with self._lock:
            self._pulse_us = float(pulse_us)

    def _median_write_ns(self, samples=40):
        write = self._lgpio.gpio_write
        handle, gpio = self._handle, self._gpio
        times = []
        for _ in range(samples):
            t0 = time.perf_counter_ns()
            write(handle, gpio, 0)
            times.append(time.perf_counter_ns() - t0)
        times.sort()
        return times[len(times) // 2]

    def stop(self):
        self._running = False
        self._thread.join(timeout=0.6)
        try:
            self._lgpio.gpio_write(self._handle, self._gpio, 0)
        except Exception:
            pass

    def _loop(self):
        write = self._lgpio.gpio_write
        handle = self._handle
        gpio = self._gpio
        period_ns = _REFRESH_US * 1000
        pulses = 0
        window_start = time.perf_counter()
        while self._running:
            with self._lock:
                pulse_ns = int(self._pulse_us * 1000)
            pulse_ns = max(500_000, min(2_500_000, pulse_ns))
            # Compte à partir du moment où la broche est déjà HIGH.
            write(handle, gpio, 1)
            start = time.perf_counter_ns()
            until = start + pulse_ns - self._off_comp_ns
            if until < start + 200_000:
                until = start + 200_000
            while time.perf_counter_ns() < until:
                pass
            write(handle, gpio, 0)
            pulses += 1
            now = time.perf_counter()
            elapsed = now - window_start
            if elapsed >= 0.5:
                self.measured_hz = pulses / elapsed
                pulses = 0
                window_start = now
            remain_ns = period_ns - (time.perf_counter_ns() - start)
            if remain_ns > 2_000_000:
                time.sleep((remain_ns - 500_000) / 1_000_000_000)
            while self._running and time.perf_counter_ns() - start < period_ns:
                pass


def _stop_lgpio_timer_pwm(lgpio_mod, handle, gpio):
    """Coupe tx_pulse/tx_pwm/tx_servo s'ils tournent encore (timer ~2,5 Hz)."""
    for call in (
        lambda: lgpio_mod.tx_pwm(handle, gpio, 0, 0),
        lambda: lgpio_mod.tx_servo(handle, gpio, 0),
        lambda: lgpio_mod.tx_pulse(handle, gpio, 0, 0),
    ):
        try:
            call()
        except Exception:
            pass


class ServoController:
    def __init__(self):
        self._angle = config.SERVO_ANGLE_DOWN
        self._lgpio = None
        self._handle = None
        self._gpio = None
        self._pwm = None

        if config.IS_RASPBERRY:
            self._attach()
            self.write(self._angle)
        else:
            print("[SIMULATION] Servo (échelle 0–180 → impulsions µs, comme Servo.write)")

    def write(self, angle):
        """Équivalent de ControlHauteurBras.write(angle)."""
        angle = max(0, min(180, int(round(angle))))
        self._angle = angle
        if self._pwm is not None:
            self._pwm.set_pulse_us(command_pulse_us(angle))

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
        pulse = command_pulse_us(config.SERVO_ANGLE_UP)
        print(f"  Servo : monter  write({config.SERVO_ANGLE_UP}) = {pulse:.0f} µs")
        self.move_to(config.SERVO_ANGLE_UP)

    def down(self):
        pulse = command_pulse_us(config.SERVO_ANGLE_DOWN)
        print(f"  Servo : descendre  write({config.SERVO_ANGLE_DOWN}) = {pulse:.0f} µs")
        self.move_to(config.SERVO_ANGLE_DOWN)

    @property
    def current_angle(self):
        return self._angle

    @property
    def measured_hz(self):
        if self._pwm is None:
            return 0.0
        return float(self._pwm.measured_hz)

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
        _stop_lgpio_timer_pwm(self._lgpio, self._handle, self._gpio)
        rest = command_pulse_us(self._angle)
        self._pwm = _GpioWritePwm(self._lgpio, self._handle, self._gpio, rest)
        print(
            f"Servo {describe(bcm)}  —  write(n) ≈ n°  "
            f"({config.SERVO_MIN_PULSE_US}–{config.SERVO_MAX_PULSE_US} µs), "
            f"gpio_write {self._pwm._off_comp_ns / 1000:.0f} µs compensés"
            f"{', INVERT' if config.SERVO_INVERT else ''}"
        )

    def _detach(self):
        if self._pwm is not None:
            self._pwm.stop()
            self._pwm = None
        if self._handle is not None and self._gpio is not None and self._lgpio is not None:
            try:
                self._lgpio.gpio_write(self._handle, self._gpio, 0)
                self._lgpio.gpio_free(self._handle, self._gpio)
            except Exception:
                pass
        self._handle = None
        self._gpio = None
        self._lgpio = None
