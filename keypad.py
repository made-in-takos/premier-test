"""
Pavé numérique 4×4 — même disposition que le sketch Arduino (Keypad.h).

    1 2 3 A
    4 5 6 B
    7 8 9 C
    * 0 # D

Sur Raspberry Pi : matrice GPIO (lignes en sortie, colonnes en entrée pull-up).
Hors Pi : file d'attente (tests) + clavier du terminal.
"""

from collections import deque
import select
import sys
import time

import config

KEYMAP = [
    ["1", "2", "3", "A"],
    ["4", "5", "6", "B"],
    ["7", "8", "9", "C"],
    ["*", "0", "#", "D"],
]


class Keypad:
    def __init__(self, simulate=None):
        self._queue = deque()
        self._last_key = None
        self._gpio = False
        self._rows = []
        self._cols = []
        self._simulate = (not config.IS_RASPBERRY) if simulate is None else simulate

        if not self._simulate:
            from gpiozero import Button, DigitalOutputDevice

            self._rows = [
                DigitalOutputDevice(pin, initial_value=True)
                for pin in config.KEYPAD_ROW_PINS
            ]
            self._cols = [
                Button(pin, pull_up=True, bounce_time=config.KEYPAD_DEBOUNCE_S)
                for pin in config.KEYPAD_COL_PINS
            ]
            self._gpio = True
        else:
            print("[SIMULATION] Pavé 4×4 — tape 0-9 A-D * # (Entrée ignorée)")

    def inject(self, keys):
        """Injecte des touches (tests unitaires)."""
        for key in keys:
            if key not in ("\n", "\r", " "):
                self._queue.append(str(key))

    def get_key(self):
        """Équivalent non bloquant de Keypad.getKey() : un caractère ou None."""
        if self._queue:
            return self._queue.popleft()

        if self._gpio:
            return self._scan_matrix()

        return self._read_stdin()

    def wait_key(self, allowed=None, timeout=None):
        """Attend une touche. `allowed` : ensemble de caractères acceptés."""
        deadline = None if timeout is None else time.time() + timeout
        while True:
            key = self.get_key()
            if key is not None and (allowed is None or key in allowed):
                return key
            if deadline is not None and time.time() >= deadline:
                return None
            time.sleep(0.02)

    def _scan_matrix(self):
        pressed = None
        for r, row in enumerate(self._rows):
            row.off()  # ligne active = LOW
            try:
                for c, col in enumerate(self._cols):
                    if col.is_pressed:
                        pressed = KEYMAP[r][c]
                        break
            finally:
                row.on()
            if pressed is not None:
                break

        if pressed is None:
            self._last_key = None
            return None

        if pressed == self._last_key:
            return None

        time.sleep(config.KEYPAD_DEBOUNCE_S)
        self._last_key = pressed
        return pressed

    def _read_stdin(self):
        try:
            if not select.select([sys.stdin], [], [], 0)[0]:
                return None
            char = sys.stdin.read(1)
        except (OSError, ValueError):
            return None
        if not char or char in ("\n", "\r"):
            return None
        key = char.upper() if char.isalpha() else char
        valid = {cell for row in KEYMAP for cell in row}
        return key if key in valid else None

    def cleanup(self):
        for row in self._rows:
            row.close()
        for col in self._cols:
            col.close()
        self._rows = []
        self._cols = []
        self._gpio = False
