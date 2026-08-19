"""
Machine à états principale : menus LCD/pavé → prise → analyse → tri.

Usage :
    python main.py
    python main.py --once
    python main.py --calibrate
    python main.py --deck magic --sort Color --count 10 --skip-test
"""

import argparse
import time

import config
from arm_controller import ArmController
from camera import Camera
from card_recognition import identify_card, load_references
from keypad import Keypad
from lcd_display import LcdDisplay
from menu import SorterSettings, SorterUI
from pneumatic import PneumaticController
from servo_controller import ServoController
from sort_tables import DECK_LABEL, drop_angle, result_label


class CardSorter:
    def __init__(self, lcd=None, keypad=None):
        self.lcd = lcd
        self.keypad = keypad
        self.arm = ArmController()
        self.servo = ServoController()
        self.pneumatic = PneumaticController()
        self.camera = None
        self.rank_refs = {}
        self.suit_refs = {}
        self.settings = SorterSettings()
        self._stop = False

    def _status(self, line1, line2=""):
        print(f"{line1} {line2}".strip())
        if self.lcd:
            self.lcd.message(line1, line2)

    def _ensure_camera(self):
        if self.camera is None:
            self.camera = Camera()

    def _ensure_playing_refs(self):
        if self.rank_refs and self.suit_refs:
            return True
        self.rank_refs, self.suit_refs = load_references()
        if self.rank_refs and self.suit_refs:
            return True
        self._status("ERREUR refs", "generate_ref")
        print(
            "Images de référence manquantes.\n"
            "Lance d'abord : python generate_references.py"
        )
        return False

    def calibrate(self):
        self.servo.up()
        self.pneumatic.to_transport_height()
        self.arm.home()

    def _identify(self, frame):
        deck = self.settings.deck
        if deck == config.DECK_PLAYING:
            if not self.rank_refs or not self.suit_refs:
                return None
            return identify_card(frame, self.rank_refs, self.suit_refs)

        # Magic / Pokémon : la vision dédiée n'est pas encore branchée
        # (le sketch Arduino renvoyait 0 / Rouge en stub).
        return None

    def _identify_with_retries(self):
        self._ensure_camera()
        for attempt in range(1, config.MAX_IDENTIFY_ATTEMPTS + 1):
            if self._abort_requested():
                return None
            frame = self.camera.capture()
            if frame is None:
                continue

            result = self._identify(frame)
            if result is None:
                print(f"  Tentative {attempt}/{config.MAX_IDENTIFY_ATTEMPTS} : carte non détectée")
                time.sleep(0.2)
                continue

            if self.settings.deck == config.DECK_PLAYING:
                rank_ok = result["rank_score"] <= config.MAX_RANK_SCORE
                suit_ok = result["suit_score"] <= config.MAX_SUIT_SCORE
                if not (rank_ok and suit_ok):
                    print(
                        f"  Tentative {attempt}/{config.MAX_IDENTIFY_ATTEMPTS} : "
                        f"{result['rank']} de {result['suit']} "
                        f"(scores {result['rank_score']}, {result['suit_score']} — incertains)"
                    )
                    time.sleep(0.2)
                    continue

            return result

        return None

    def _abort_requested(self):
        if self._stop:
            return True
        if self.keypad is None:
            return False
        key = self.keypad.get_key()
        if key in ("*", "C"):
            self._stop = True
            self._status("Arret", "demande")
            return True
        return False

    def _pick_card(self):
        self.arm.move_to(config.PICKUP_ANGLE)
        self.pneumatic.to_pickup_height()
        self.servo.down()
        self.pneumatic.pick()
        self.servo.up()
        self.pneumatic.to_transport_height()

    def _release_card(self):
        self.pneumatic.to_deposit_height()
        self.servo.down()
        self.pneumatic.release()
        self.servo.up()
        self.pneumatic.to_transport_height()

    def process_one_card(self, remaining=None):
        prefix = f"{remaining} " if remaining is not None else ""
        print("\n--- Prise de carte ---")
        if remaining is not None:
            self._status(str(remaining), "prise...")
        self._pick_card()

        print("--- Analyse ---")
        self.arm.move_to(config.CAMERA_ANGLE)
        time.sleep(0.3)

        result = self._identify_with_retries()
        if result is None:
            print("Échec identification — bac inconnu / retour zéro")
            angle = config.HOME_ANGLE
            label = "Inconnue"
        else:
            angle = drop_angle(self.settings.deck, self.settings.sort_mode, result)
            label = result_label(self.settings.deck, result)
            print(f"Carte identifiée : {label} → {angle}°")

        self._status(f"{prefix}{label}"[:16], str(int(angle)))
        self.arm.move_to(angle)
        self._release_card()
        self.arm.move_to(config.HOME_ANGLE)
        return result is not None

    def run(self, settings, loop=False):
        self.settings = settings
        self._stop = False

        if settings.deck == config.DECK_PLAYING and not self._ensure_playing_refs():
            return

        try:
            self.servo.up()
            self.pneumatic.to_transport_height()

            remaining = settings.card_count
            processed = 0
            while remaining > 0 and not self._stop:
                ok = self.process_one_card(remaining=remaining)
                remaining -= 1
                if ok:
                    processed += 1
                if not loop and remaining <= 0:
                    break
                time.sleep(0.5)

            self._status("Termine", f"{processed} cartes")
        except KeyboardInterrupt:
            print("\nArrêt demandé.")
            self._status("Arret", "")

    def cleanup(self):
        self.pneumatic.cleanup()
        self.servo.cleanup()
        self.arm.cleanup()
        if self.camera is not None:
            self.camera.cleanup()
            self.camera = None


def build_parser():
    parser = argparse.ArgumentParser(description="Trieur de cartes Raspberry Pi")
    parser.add_argument("--once", action="store_true", help="Une seule carte (ignore le nombre saisi)")
    parser.add_argument("--calibrate", action="store_true", help="Homing + mise à zéro clavier")
    parser.add_argument("--skip-test", action="store_true", help="Saute le mode En test")
    parser.add_argument("--skip-menu", action="store_true", help="Saute tous les menus LCD")
    parser.add_argument(
        "--deck",
        choices=[config.DECK_PLAYING, config.DECK_POKEMON, config.DECK_MAGIC],
        help="Type de cartes (playing, pokemon, magic)",
    )
    parser.add_argument("--sort", help="Mode de tri (Color, Type, Cost, Rarity, Rank, RedBlack, Category)")
    parser.add_argument("--count", type=int, help="Nombre de cartes à traiter")
    return parser


def main():
    args = build_parser().parse_args()

    lcd = LcdDisplay()
    keypad = Keypad()
    sorter = CardSorter(lcd=lcd, keypad=keypad)
    ui = SorterUI(
        keypad,
        lcd,
        arm=sorter.arm,
        servo=sorter.servo,
        pneumatic=sorter.pneumatic,
    )

    try:
        lcd.begin(16, 2)
        sorter.servo.up()

        if args.calibrate:
            ui.manual_home()
            sorter.calibrate()
            return

        settings = SorterSettings(
            deck=args.deck or "",
            sort_mode=args.sort or "",
            card_count=args.count or 0,
        )
        if args.skip_menu:
            sorter.arm.home()
            settings.deck = settings.deck or config.DEFAULT_DECK
            settings.sort_mode = settings.sort_mode or config.DEFAULT_SORT_MODE
            settings.card_count = settings.card_count or 1
        else:
            ui.manual_home()
            if not args.skip_test:
                ui.run_hardware_tests()
            settings = ui.run_menus(settings)

        if args.once:
            settings.card_count = 1

        print(
            f"Démarrage : {DECK_LABEL.get(settings.deck, settings.deck)} / "
            f"{settings.sort_mode} / {settings.card_count} cartes"
        )
        sorter.run(settings, loop=False)
    finally:
        sorter.cleanup()
        keypad.cleanup()
        lcd.cleanup()


if __name__ == "__main__":
    main()
