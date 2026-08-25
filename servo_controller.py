"""
Contrôle du servomoteur d'inclinaison du bras.

Sur Raspberry Pi 5, gpiozero.AngularServo (PWM logiciel) ne génère
souvent aucun mouvement. On utilise dans l'ordre :
  1. lgpio.tx_pwm  — PWM cadencé par le chip RP1 (recommandé Pi 5)
  2. gpiozero PWMOutputDevice
  3. impulsions 50 Hz dans un thread (DigitalOutputDevice)
"""

from __future__ import annotations

import glob
import threading
import time

import config


def angle_to_pulse_us(angle: float) -> float:
    angle = max(0.0, min(180.0, float(angle)))
    span = config.SERVO_MAX_PULSE_US - config.SERVO_MIN_PULSE_US
    return config.SERVO_MIN_PULSE_US + (angle / 180.0) * span


def pulse_us_to_duty(pulse_us: float, hz: float | None = None) -> float:
    hz = hz if hz is not None else config.SERVO_PWM_HZ
    period_us = 1_000_000.0 / hz
    return max(0.0, min(100.0, (pulse_us / period_us) * 100.0))


def _gpiochip_candidates():
    """Pi 5 : GPIOs du header = gpiochip4 (RP1). Pi 4 : gpiochip0."""
    chips = []
    try:
        with open("/proc/device-tree/model", encoding="utf-8") as f:
            model = f.read().lower()
    except OSError:
        model = ""
    if "raspberry pi 5" in model or "rp1" in model:
        chips.append(4)
    paths = sorted(glob.glob("/dev/gpiochip*"))
    for path in paths:
        try:
            chips.append(int(path.replace("/dev/gpiochip", "")))
        except ValueError:
            continue
    chips.extend((4, 0, 1))
    seen = set()
    ordered = []
    for chip in chips:
        if chip not in seen:
            seen.add(chip)
            ordered.append(chip)
    return ordered


class ServoController:
    def __init__(self):
        self._current_angle = config.SERVO_ANGLE_UP
        self._backend = "sim"
        self._lgpio = None
        self._handle = None
        self._pwm = None
        self._pin = None
        self._thread = None
        self._alive = False
        self._pulse_us = angle_to_pulse_us(config.SERVO_ANGLE_UP)
        self._lock = threading.Lock()

        if not config.IS_RASPBERRY:
            print("[SIMULATION] Servomoteur inclinaison")
            return

        preferred = (config.SERVO_BACKEND or "auto").lower()
        errors = []

        if preferred in ("auto", "lgpio"):
            try:
                self._init_lgpio()
            except Exception as exc:
                errors.append(f"lgpio: {exc}")
                if preferred == "lgpio":
                    raise

        if self._backend == "sim" and preferred in ("auto", "gpiozero"):
            try:
                self._init_gpiozero_pwm()
            except Exception as exc:
                errors.append(f"gpiozero PWM: {exc}")
                if preferred == "gpiozero":
                    raise

        if self._backend == "sim" and preferred in ("auto", "thread"):
            try:
                self._init_thread_pwm()
            except Exception as exc:
                errors.append(f"thread PWM: {exc}")
                raise RuntimeError(
                    "Impossible de piloter le servo. " + " | ".join(errors)
                ) from exc

        self._apply_pulse(self._pulse_us)
        print(
            f"Servo GPIO {config.GPIO_SERVO_TILT} via {self._backend} "
            f"({self._pulse_us:.0f} µs, {config.SERVO_PWM_HZ} Hz)"
        )

    def _init_lgpio(self):
        import lgpio

        pin = config.GPIO_SERVO_TILT
        last_error = None
        for chip in _gpiochip_candidates():
            handle = None
            try:
                handle = lgpio.gpiochip_open(chip)
                lgpio.gpio_claim_output(handle, pin)
                self._lgpio = lgpio
                self._handle = handle
                self._backend = "lgpio"
                print(f"  lgpio gpiochip{chip}, GPIO {pin}")
                return
            except Exception as exc:
                last_error = exc
                if handle is not None:
                    try:
                        lgpio.gpiochip_close(handle)
                    except Exception:
                        pass
        raise RuntimeError(last_error or "aucun gpiochip lgpio")

    def _init_gpiozero_pwm(self):
        from gpiozero import PWMOutputDevice

        duty = pulse_us_to_duty(self._pulse_us) / 100.0
        self._pwm = PWMOutputDevice(
            config.GPIO_SERVO_TILT,
            frequency=config.SERVO_PWM_HZ,
            initial_value=duty,
        )
        try:
            self._pwm.frequency = config.SERVO_PWM_HZ
        except Exception:
            pass
        self._backend = "gpiozero"
        print(f"  gpiozero PWM {config.SERVO_PWM_HZ} Hz, duty={duty:.4f}")

    def _init_thread_pwm(self):
        from gpiozero import DigitalOutputDevice

        self._pin = DigitalOutputDevice(config.GPIO_SERVO_TILT, initial_value=False)
        self._alive = True
        self._thread = threading.Thread(target=self._pwm_loop, daemon=True)
        self._thread.start()
        self._backend = "thread"

    def _pwm_loop(self):
        period = 1.0 / config.SERVO_PWM_HZ
        while self._alive:
            with self._lock:
                pulse_s = self._pulse_us / 1_000_000.0
            if self._pin is None or pulse_s <= 0:
                time.sleep(period)
                continue
            self._pin.on()
            time.sleep(pulse_s)
            self._pin.off()
            off_s = period - pulse_s
            if off_s > 0:
                time.sleep(off_s)

    def _apply_pulse(self, pulse_us: float):
        pulse_us = max(config.SERVO_MIN_PULSE_US, min(config.SERVO_MAX_PULSE_US, pulse_us))
        with self._lock:
            self._pulse_us = pulse_us
        duty = pulse_us_to_duty(pulse_us)

        if self._backend == "lgpio" and self._lgpio and self._handle is not None:
            self._lgpio.tx_pwm(
                self._handle,
                config.GPIO_SERVO_TILT,
                config.SERVO_PWM_HZ,
                duty,
            )
        elif self._backend == "gpiozero" and self._pwm is not None:
            self._pwm.value = duty / 100.0
        # thread backend lit _pulse_us tout seul

    def _stop_pwm(self):
        self._alive = False
        if self._thread is not None:
            self._thread.join(timeout=0.5)
            self._thread = None
        if self._backend == "lgpio" and self._lgpio and self._handle is not None:
            try:
                self._lgpio.tx_pwm(self._handle, config.GPIO_SERVO_TILT, 0, 0)
            except Exception:
                pass
            try:
                self._lgpio.gpio_free(self._handle, config.GPIO_SERVO_TILT)
            except Exception:
                pass
            try:
                self._lgpio.gpiochip_close(self._handle)
            except Exception:
                pass
            self._handle = None
        if self._pwm is not None:
            try:
                self._pwm.off()
                self._pwm.close()
            except Exception:
                pass
            self._pwm = None
        if self._pin is not None:
            try:
                self._pin.off()
                self._pin.close()
            except Exception:
                pass
            self._pin = None

    def move_to(self, angle, wait=True):
        target = max(0.0, min(180.0, float(angle)))
        start = self._current_angle
        step_ms = config.SERVO_MS_PER_DEG

        if wait and step_ms > 0 and abs(target - start) >= 1:
            direction = 1 if target > start else -1
            angle = start
            while (direction > 0 and angle < target) or (direction < 0 and angle > target):
                angle += direction
                if (direction > 0 and angle > target) or (direction < 0 and angle < target):
                    angle = target
                self._apply_pulse(angle_to_pulse_us(angle))
                self._current_angle = angle
                time.sleep(step_ms / 1000.0)
        else:
            self._apply_pulse(angle_to_pulse_us(target))
            self._current_angle = target
            if wait:
                time.sleep(config.SERVO_SETTLE_S)
            return

        self._apply_pulse(angle_to_pulse_us(target))
        self._current_angle = target
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

    @property
    def backend(self):
        return self._backend

    def cleanup(self, park=True):
        if self._backend == "sim":
            return
        try:
            if park:
                self.move_to(config.SERVO_ANGLE_UP)
        except Exception:
            pass
        self._stop_pwm()
