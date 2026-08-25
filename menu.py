"""
Menus LCD + pavé — portage du loop() Arduino, plus le choix du type de cartes.

Flux :
  1. Mise à zéro manuelle du stepper (# pour valider)
  2. Mode test matériel (1 servo, 2 rotation, 3 relais, # suite)
  3. Type de cartes : 1 Jeu 52 / 2 Pokémon / 3 Magic
  4. Mode de tri (selon le jeu, comme 1:C 2:T 3:P 4:R)
  5. Nombre de cartes (chiffres, # valider, * effacer)
"""

from dataclasses import dataclass
import time

import config
from sort_tables import (
    DECK_FROM_KEY,
    DECK_LABEL,
    DEFAULT_COUNT,
    lcd_sort_line,
    sort_label,
    sort_mode_from_key,
)


@dataclass
class SorterSettings:
    deck: str = ""
    sort_mode: str = ""
    card_count: int = 0


def _sleep(seconds):
    if seconds:
        time.sleep(seconds)


class SorterUI:
    def __init__(self, keypad, lcd, arm=None, servo=None, pneumatic=None):
        self.keypad = keypad
        self.lcd = lcd
        self.arm = arm
        self.servo = servo
        self.pneumatic = pneumatic

    # --- FCTMiseAZeroStepper ---

    def manual_home(self):
        """Jog clavier jusqu'à ce que la position de départ convienne, puis #."""
        self.lcd.message("Start pos ok ?", "1/2 4/5 7/8  #")
        while True:
            key = self.keypad.wait_key()
            if key is None:
                continue
            if key == "#":
                if self.arm:
                    self.arm.mark_as_zero()
                self.lcd.message("Zero OK", "")
                _sleep(config.LCD_MESSAGE_DELAY_S)
                return
            if self.arm is None:
                continue
            moves = {
                "1": 1,
                "2": -1,
                "4": 5,
                "5": -5,
                "7": 20,
                "8": -20,
            }
            delta = moves.get(key)
            if delta is None:
                continue
            self.arm.move_by(delta)
            self.lcd.set_cursor(0, 1)
            self.lcd.print(f"{delta:+d}            ")

    # --- Mode "En test" du loop() Arduino ---

    def run_hardware_tests(self):
        self.lcd.message("En test", "# pour menu")
        while True:
            key = self.keypad.wait_key()
            if key is None:
                continue
            if key == "#":
                return
            if key == "1":
                self._test_servo()
            elif key == "2":
                self._test_stepper()
            elif key == "3":
                self._test_relays()
            elif key == "4":
                self.lcd.message("En test", "skip")

    def _test_servo(self):
        self.lcd.message("Test servo", "haut bas")
        if not self.servo:
            return
        self.servo.up()
        self.servo.down()
        self.servo.up()
        self.servo.down()
        self.lcd.message("En test", "# pour menu")

    def _test_stepper(self):
        self.lcd.message("Test rotation", "2")
        if not self.arm:
            _sleep(config.HARDWARE_TEST_HOLD_S)
            return
        self.arm.move_to(45)
        _sleep(config.HARDWARE_TEST_HOLD_S)
        self.arm.move_to(-45)
        _sleep(config.HARDWARE_TEST_HOLD_S)
        self.arm.move_to(0)
        self.lcd.message("En test", "# pour menu")

    def _test_relays(self):
        self.lcd.message("Test relais", "3")
        hold = config.HARDWARE_TEST_HOLD_S
        if not self.pneumatic:
            _sleep(hold)
            return
        self.pneumatic._set("pump_card", True)
        _sleep(hold)
        self.pneumatic._set("pump_card", False)
        _sleep(hold)
        self.pneumatic._set("valve_card", True)
        _sleep(hold)
        self.pneumatic._set("valve_card", False)
        _sleep(hold)
        self.pneumatic._set("pump_lift", True)
        _sleep(hold)
        self.pneumatic._set("pump_lift", False)
        _sleep(hold)
        self.pneumatic._set("valve_lift", True)
        _sleep(hold)
        self.pneumatic._set("valve_lift", False)
        self.lcd.message("En test", "# pour menu")

    # --- Nouveau : type de cartes ---

    def select_deck(self):
        """Même principe que Select Mode : une touche = un choix."""
        while True:
            self.lcd.message("Select deck", "1:52 2:Pkm 3:Mag")
            key = self.keypad.wait_key()
            if key == "*":
                continue
            deck = DECK_FROM_KEY.get(key)
            if deck is None:
                self.lcd.message("No deck selected", "")
                _sleep(config.LCD_MESSAGE_DELAY_S)
                continue
            label = DECK_LABEL[deck]
            self.lcd.message("Vous avez choisi", label)
            _sleep(config.LCD_MESSAGE_DELAY_S)
            return deck

    # --- FCTSelectionModeTri ---

    def select_sort_mode(self, deck_id):
        while True:
            self.lcd.message("Select Mode", lcd_sort_line(deck_id))
            key = self.keypad.wait_key()
            if key == "*":
                return None
            mode = sort_mode_from_key(deck_id, key)
            if mode is None:
                self.lcd.message("No mode selected", "")
                _sleep(config.LCD_MESSAGE_DELAY_S)
                continue
            self.lcd.message("Vous avez choisi", f"le mode {sort_label(deck_id, mode)}")
            _sleep(config.LCD_MESSAGE_DELAY_S)
            return mode

    # --- FCTNombreDeCarte ---

    def enter_card_count(self, default=0):
        self.lcd.message("Veuillez entrer", "le nombre de")
        _sleep(config.LCD_MESSAGE_DELAY_S)
        self.lcd.message("le nombre de", "carte a traiter.")
        _sleep(config.LCD_MESSAGE_DELAY_S)

        digits = ""
        self._show_count_prompt(digits, default)
        while True:
            key = self.keypad.wait_key()
            if key is None:
                continue
            if key.isdigit() and len(digits) < 3:
                digits += key
                self._show_count_prompt(digits, default)
            elif key == "*":
                digits = ""
                self.lcd.message("Nombre efface", "")
                _sleep(config.LCD_MESSAGE_DELAY_S)
                self._show_count_prompt(digits, default)
            elif key == "#":
                if digits:
                    count = int(digits)
                else:
                    count = default
                if count <= 0 or count > config.MAX_CARD_COUNT:
                    self.lcd.message("Nombre invalide", "")
                    _sleep(config.LCD_MESSAGE_DELAY_S)
                    digits = ""
                    self._show_count_prompt(digits, default)
                    continue
                self.lcd.message("Nombre choisi:", str(count))
                _sleep(config.LCD_CONFIRM_DELAY_S)
                return count

    def _show_count_prompt(self, digits, default):
        shown = digits if digits else (str(default) if default else "")
        self.lcd.message("Nombre choisi:", shown)

    def run_menus(self, settings=None):
        """Enchaîne type de jeu → mode de tri → nombre de cartes."""
        settings = settings or SorterSettings()

        if not settings.deck:
            settings.deck = self.select_deck()
        else:
            self.lcd.message("Vous avez choisi", DECK_LABEL.get(settings.deck, settings.deck))
            _sleep(config.LCD_MESSAGE_DELAY_S)

        if not settings.sort_mode:
            mode = self.select_sort_mode(settings.deck)
            while mode is None:
                settings.deck = self.select_deck()
                mode = self.select_sort_mode(settings.deck)
            settings.sort_mode = mode

        if not settings.card_count:
            default = DEFAULT_COUNT.get(settings.deck, 52)
            settings.card_count = self.enter_card_count(default=default)

        self.lcd.message(
            DECK_LABEL.get(settings.deck, settings.deck),
            f"{settings.sort_mode} n={settings.card_count}",
        )
        _sleep(config.LCD_MESSAGE_DELAY_S)
        return settings
