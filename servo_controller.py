"""
Servomoteur d'inclinaison — même usage que le sketch Arduino.

    ControlHauteurBras.attach(23);
    ControlHauteurBras.write(50);          # write(angle)
    FCTControlleServo(130, 40);            # write() + balayage

Le Pi n'a pas la bibliothèque Servo.h : les impulsions 50 Hz sont
générées ici, avec les mêmes bornes qu'Arduino (544–2400 µs).
"""

import glob
import threading
import time

import config

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
        self._write_pin = None
        self._handle = None
        self._lgpio = None
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
        pin = config.GPIO_SERVO_TILT
        try:
            import lgpio

            handle, _chip = _open_chip(lgpio, pin)
            self._lgpio = lgpio
            self._handle = handle

            def _write(level, _lgpio=lgpio, _handle=handle, _pin=pin):
                _lgpio.gpio_write(_handle, _pin, level)

            self._write_pin = _write
        except Exception:
            from gpiozero import DigitalOutputDevice

            self._pin = DigitalOutputDevice(pin, initial_value=False)
            gpio_pin = self._pin
            self._write_pin = lambda level, _p=gpio_pin: _p.on() if level else _p.off()

        self._running = True
        self._thread = threading.Thread(target=self._refresh, daemon=True)
        self._thread.start()

    def _refresh(self):
        """Trame servo 50 Hz, comme la bibliothèque Arduino."""
        period_ns = _REFRESH_US * 1000
        while self._running:
            with self._lock:
                pulse_ns = int(self._pulse_us * 1000)
            start = time.perf_counter_ns()
            self._write_pin(1)
            while time.perf_counter_ns() - start < pulse_ns:
                pass
            self._write_pin(0)
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
        if self._lgpio and self._handle is not None:
            try:
                self._lgpio.gpio_write(self._handle, config.GPIO_SERVO_TILT, 0)
                self._lgpio.gpio_free(self._handle, config.GPIO_SERVO_TILT)
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


def _open_chip(lgpio, pin):
    chips = []
    for path in sorted(glob.glob("/dev/gpiochip*")):
        try:
            chips.append(int(path.replace("/dev/gpiochip", "")))
        except ValueError:
            continue
    if 4 in chips:
        chips = [4] + [c for c in chips if c != 4]
    last_error = None
    for chip in chips:
        handle = None
        try:
            handle = lgpio.gpiochip_open(chip)
            lgpio.gpio_claim_output(handle, pin)
            return handle, chip
        except Exception as exc:
            last_error = exc
            if handle is not None:
                try:
                    lgpio.gpiochip_close(handle)
                except Exception:
                    pass
    raise RuntimeError(last_error or "gpiochip")
