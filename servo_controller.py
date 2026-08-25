"""
Contrôle du servomoteur d'inclinaison du bras.

Le bras au repos est en **position basse** (comme au démarrage mécanique).
Angles calqués sur l'Arduino : 50° relevé, 130° baissé.

Sur Pi 5, lgpio.tx_pwm à 50 Hz arrondit souvent le duty à 0 % : le servo
n'est plus alimenté et le bras retombe. On génère donc les impulsions
nous-mêmes (busy-wait ~1,5 ms, 50 Hz).
"""

from __future__ import annotations

import glob
import threading
import time

import config


def angle_to_pulse_us(angle: float) -> float:
    angle = max(0.0, min(180.0, float(angle)))
    if config.SERVO_INVERT:
        angle = 180.0 - angle
    span = config.SERVO_MAX_PULSE_US - config.SERVO_MIN_PULSE_US
    return config.SERVO_MIN_PULSE_US + (angle / 180.0) * span


def pulse_us_to_duty(pulse_us: float, hz: float | None = None) -> float:
    hz = hz if hz is not None else config.SERVO_PWM_HZ
    period_us = 1_000_000.0 / hz
    return max(0.0, min(100.0, (pulse_us / period_us) * 100.0))


def _gpiochip_candidates():
    chips = []
    try:
        with open("/proc/device-tree/model", encoding="utf-8") as f:
            model = f.read().lower()
    except OSError:
        model = ""
    if "raspberry pi 5" in model or "rp1" in model:
        chips.append(4)
    for path in sorted(glob.glob("/dev/gpiochip*")):
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
        # Repos = position basse (le bras commence baissé).
        self._current_angle = config.SERVO_ANGLE_DOWN
        self._backend = "sim"
        self._lgpio = None
        self._handle = None
        self._pin = None
        self._thread = None
        self._alive = False
        self._pulse_us = angle_to_pulse_us(config.SERVO_ANGLE_DOWN)
        self._lock = threading.Lock()

        if not config.IS_RASPBERRY:
            print("[SIMULATION] Servomoteur — repos en position basse")
            return

        preferred = (config.SERVO_BACKEND or "auto").lower()
        errors = []

        # busywait d'abord : c'est le seul PWM servo fiable sur Pi 5 / RP1.
        if preferred in ("auto", "busywait", "thread"):
            try:
                self._init_busywait()
            except Exception as exc:
                errors.append(f"busywait: {exc}")
                if preferred in ("busywait", "thread"):
                    raise

        if self._backend == "sim" and preferred in ("auto", "lgpio"):
            try:
                self._init_lgpio_tx()
            except Exception as exc:
                errors.append(f"lgpio tx_pwm: {exc}")
                if preferred == "lgpio":
                    raise

        if self._backend == "sim":
            raise RuntimeError("Impossible de piloter le servo. " + " | ".join(errors))

        self._apply_pulse(self._pulse_us)
        print(
            f"Servo GPIO {config.GPIO_SERVO_TILT} via {self._backend} "
            f"— repos {config.SERVO_ANGLE_DOWN:.0f}° ({self._pulse_us:.0f} µs)"
        )

    def _init_busywait(self):
        """Impulsions 50 Hz en busy-wait (largeur ~µs exacte)."""
        pin = config.GPIO_SERVO_TILT
        try:
            import lgpio
        except ImportError:
            self._init_busywait_gpiozero()
            return

        last_error = None
        for chip in _gpiochip_candidates():
            handle = None
            try:
                handle = lgpio.gpiochip_open(chip)
                lgpio.gpio_claim_output(handle, pin)
                self._lgpio = lgpio
                self._handle = handle
                self._alive = True
                self._backend = "busywait"
                self._thread = threading.Thread(target=self._busywait_lgpio_loop, daemon=True)
                self._thread.start()
                print(f"  PWM busywait lgpio gpiochip{chip} GPIO {pin}")
                return
            except Exception as exc:
                last_error = exc
                if handle is not None:
                    try:
                        lgpio.gpiochip_close(handle)
                    except Exception:
                        pass
        raise RuntimeError(last_error or "lgpio busywait")

    def _init_busywait_gpiozero(self):
        from gpiozero import DigitalOutputDevice

        self._pin = DigitalOutputDevice(config.GPIO_SERVO_TILT, initial_value=False)
        self._alive = True
        self._backend = "busywait"
        self._thread = threading.Thread(target=self._busywait_gpiozero_loop, daemon=True)
        self._thread.start()
        print(f"  PWM busywait gpiozero GPIO {config.GPIO_SERVO_TILT}")

    def _init_lgpio_tx(self):
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
                return
            except Exception as exc:
                last_error = exc
                if handle is not None:
                    try:
                        lgpio.gpiochip_close(handle)
                    except Exception:
                        pass
        raise RuntimeError(last_error or "lgpio tx_pwm")

    def _busywait_lgpio_loop(self):
        write = self._lgpio.gpio_write
        handle = self._handle
        pin = config.GPIO_SERVO_TILT
        period_ns = int(1_000_000_000 / config.SERVO_PWM_HZ)
        while self._alive:
            with self._lock:
                pulse_ns = int(self._pulse_us * 1000)
            start = time.perf_counter_ns()
            write(handle, pin, 1)
            while time.perf_counter_ns() - start < pulse_ns:
                pass
            write(handle, pin, 0)
            rest = period_ns - (time.perf_counter_ns() - start)
            if rest > 2_000_000:
                time.sleep((rest - 400_000) / 1_000_000_000)
            while time.perf_counter_ns() - start < period_ns:
                pass

    def _busywait_gpiozero_loop(self):
        period_ns = int(1_000_000_000 / config.SERVO_PWM_HZ)
        pin = self._pin
        while self._alive:
            with self._lock:
                pulse_ns = int(self._pulse_us * 1000)
            if pin is None:
                time.sleep(0.02)
                continue
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

    def _apply_pulse(self, pulse_us: float):
        pulse_us = max(config.SERVO_MIN_PULSE_US, min(config.SERVO_MAX_PULSE_US, pulse_us))
        with self._lock:
            self._pulse_us = pulse_us
        if self._backend == "lgpio" and self._lgpio and self._handle is not None:
            duty = pulse_us_to_duty(pulse_us)
            self._lgpio.tx_pwm(
                self._handle,
                config.GPIO_SERVO_TILT,
                config.SERVO_PWM_HZ,
                duty,
            )

    def _stop_pwm(self):
        self._alive = False
        if self._thread is not None:
            self._thread.join(timeout=0.5)
            self._thread = None
        if self._lgpio and self._handle is not None:
            try:
                self._lgpio.gpio_write(self._handle, config.GPIO_SERVO_TILT, 0)
            except Exception:
                pass
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
            current = start
            while (direction > 0 and current < target) or (direction < 0 and current > target):
                current += direction
                if (direction > 0 and current > target) or (direction < 0 and current < target):
                    current = target
                self._apply_pulse(angle_to_pulse_us(current))
                self._current_angle = current
                time.sleep(step_ms / 1000.0)

        self._apply_pulse(angle_to_pulse_us(target))
        self._current_angle = target
        if wait:
            time.sleep(config.SERVO_SETTLE_S)

    def up(self):
        """Bras relevé — position transport (50° sur l'Arduino)."""
        print(f"  Servo : bras relevé ({config.SERVO_ANGLE_UP:.0f}°)")
        self.move_to(config.SERVO_ANGLE_UP)

    def down(self):
        """Bras baissé — prise / dépôt / repos (130° sur l'Arduino)."""
        print(f"  Servo : bras baissé ({config.SERVO_ANGLE_DOWN:.0f}°)")
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
                self.down()
        except Exception:
            pass
        self._stop_pwm()
