"""
Afficheur LCD 16×2 HD44780 en 4 bits, comme LiquidCrystal(RS, E, D4, D5, D6, D7).

RW est câblé à GND. Hors Raspberry Pi, l'affichage est simulé dans le terminal.
"""

import time

import config


class LcdDisplay:
    def __init__(self, simulate=None):
        self.cols = config.LCD_COLS
        self.rows = config.LCD_ROWS
        self._simulate = (not config.IS_RASPBERRY) if simulate is None else simulate
        self._rs = self._e = None
        self._data = []
        self._cursor_col = 0
        self._cursor_row = 0
        self.lines = [""] * self.rows
        self.history = []

        if self._simulate:
            print("[SIMULATION] LCD 16×2")
            return

        from gpiozero import DigitalOutputDevice

        self._rs = DigitalOutputDevice(config.LCD_RS, initial_value=False)
        self._e = DigitalOutputDevice(config.LCD_E, initial_value=False)
        self._data = [
            DigitalOutputDevice(pin, initial_value=False)
            for pin in config.LCD_DATA_PINS
        ]
        self.begin(self.cols, self.rows)

    def begin(self, cols=None, rows=None):
        if cols:
            self.cols = cols
        if rows:
            self.rows = rows
        self.lines = [""] * self.rows
        if self._simulate:
            return

        time.sleep(0.05)
        self._write_nibble(0x03, rs=False)
        time.sleep(0.005)
        self._write_nibble(0x03, rs=False)
        time.sleep(0.001)
        self._write_nibble(0x03, rs=False)
        self._write_nibble(0x02, rs=False)  # passage en 4 bits
        self._command(0x28)  # 4 bits, 2 lignes, 5×8
        self._command(0x0C)  # display ON, curseur OFF
        self.clear()
        self._command(0x06)  # incrément, pas de shift

    def clear(self):
        self.lines = [""] * self.rows
        self._cursor_col = 0
        self._cursor_row = 0
        self.history.append(("", ""))
        if self._simulate:
            self._print_sim()
            return
        self._command(0x01)
        time.sleep(0.002)

    def set_cursor(self, col, row):
        """Équivalent de lcd.setCursor(col, row)."""
        self._cursor_col = max(0, min(self.cols - 1, int(col)))
        self._cursor_row = max(0, min(self.rows - 1, int(row)))
        if self._simulate:
            return
        ddram = 0x00 if self._cursor_row == 0 else 0x40
        if self._cursor_row >= 2:
            ddram = 0x14 if self._cursor_row == 2 else 0x54
        self._command(0x80 | (ddram + self._cursor_col))

    def print(self, text):
        """Équivalent de lcd.print(...)."""
        text = "" if text is None else str(text)
        row = self._cursor_row
        col = self._cursor_col
        line = list(self.lines[row].ljust(self.cols)[: self.cols])
        for char in text:
            if col >= self.cols:
                break
            line[col] = char
            if not self._simulate:
                self._write_byte(ord(char), rs=True)
            col += 1
        self.lines[row] = "".join(line).rstrip()
        self._cursor_col = col
        self._snapshot()
        if self._simulate:
            self._print_sim()

    def message(self, line1, line2=""):
        """Efface puis affiche deux lignes (raccourci pour les menus)."""
        self.clear()
        self.set_cursor(0, 0)
        self.print(_fit(line1, self.cols))
        self.set_cursor(0, 1)
        self.print(_fit(line2, self.cols))

    def snapshot(self):
        return tuple(line.ljust(self.cols)[: self.cols] for line in self.lines)

    def _snapshot(self):
        self.history.append(self.snapshot())

    def _print_sim(self):
        line1, line2 = self.snapshot()
        print(f"[LCD] |{line1}|")
        print(f"      |{line2}|")

    def _command(self, value):
        self._write_byte(value, rs=False)

    def _write_byte(self, value, rs):
        self._write_nibble((value >> 4) & 0x0F, rs)
        self._write_nibble(value & 0x0F, rs)

    def _write_nibble(self, nibble, rs):
        self._rs.value = bool(rs)
        for bit, pin in enumerate(self._data):
            pin.value = bool((nibble >> bit) & 1)
        self._pulse_enable()

    def _pulse_enable(self):
        self._e.off()
        time.sleep(0.000001)
        self._e.on()
        time.sleep(0.000001)
        self._e.off()
        time.sleep(0.00005)

    def cleanup(self):
        if self._simulate:
            return
        try:
            self.clear()
        except Exception:
            pass
        for dev in [self._rs, self._e, *self._data]:
            if dev is not None:
                dev.close()
        self._rs = self._e = None
        self._data = []


def _fit(text, width):
    text = "" if text is None else str(text)
    return text[:width]
