"""Tests des menus LCD/pavé et des tables de tri (sans GPIO)."""

import config
from keypad import KEYMAP, Keypad
from lcd_display import LcdDisplay
from menu import SorterSettings, SorterUI
from sort_tables import (
    DECK_FROM_KEY,
    drop_angle,
    lcd_sort_line,
    magic_color_angle,
    sort_mode_from_key,
)


def test_magic_color_angles_match_arduino():
    step = 18
    assert magic_color_angle("Rouge") == step * -1
    assert magic_color_angle("Red") == step * -1
    assert magic_color_angle("Bleu") == step * -2
    assert magic_color_angle("Gruul") == step * -10
    assert magic_color_angle("Izzet") == step * 1
    assert magic_color_angle("Grixis") == step * 9
    assert magic_color_angle("WUBRG") == step * 9
    assert magic_color_angle("Colorless") == step * 1
    assert magic_color_angle("Jeskai") == step * -1
    assert magic_color_angle("Inconnu") == 0


def test_playing_suit_and_color_bins():
    hearts = {"rank": "Ace", "suit": "Hearts"}
    spades = {"rank": "10", "suit": "Spades"}
    assert drop_angle(config.DECK_PLAYING, "Color", hearts) == config.SORT_ANGLES["Hearts"]
    assert drop_angle(config.DECK_PLAYING, "RedBlack", hearts) == config.SORT_ANGLES["Hearts"]
    assert drop_angle(config.DECK_PLAYING, "RedBlack", spades) == config.SORT_ANGLES["Spades"]
    assert drop_angle(config.DECK_PLAYING, "Rank", {"rank": "King", "suit": "Hearts"}) == 75.0
    assert drop_angle(config.DECK_PLAYING, "Rank", {"rank": "Ace", "suit": "Hearts"}) == -75.0


def test_pokemon_and_magic_type_angles():
    assert drop_angle(config.DECK_POKEMON, "Type", {"type": "Fire"}) == 18 * -1
    assert drop_angle(config.DECK_POKEMON, "Category", {"category": "Trainer"}) == 18 * 1
    assert drop_angle(config.DECK_MAGIC, "Type", {"type": "Creature"}) == 18 * -1
    assert drop_angle(config.DECK_MAGIC, "Cost", {"cost": 6}) == 18 * 3
    assert drop_angle(config.DECK_MAGIC, "Rarity", {"rarity": "Mythic"}) == 18 * 2


def test_deck_and_sort_keys():
    assert DECK_FROM_KEY["1"] == config.DECK_PLAYING
    assert DECK_FROM_KEY["2"] == config.DECK_POKEMON
    assert DECK_FROM_KEY["3"] == config.DECK_MAGIC
    assert sort_mode_from_key(config.DECK_MAGIC, "1") == "Color"
    assert sort_mode_from_key(config.DECK_MAGIC, "2") == "Type"
    assert sort_mode_from_key(config.DECK_MAGIC, "3") == "Cost"
    assert sort_mode_from_key(config.DECK_MAGIC, "4") == "Rarity"
    assert lcd_sort_line(config.DECK_MAGIC) == "1:C 2:T 3:P 4:R"
    assert sort_mode_from_key(config.DECK_PLAYING, "3") == "RedBlack"
    assert sort_mode_from_key(config.DECK_MAGIC, "9") is None


def test_menu_full_flow_magic():
    keypad = Keypad(simulate=True)
    lcd = LcdDisplay(simulate=True)
    ui = SorterUI(keypad, lcd)
    keypad.inject("3152#")  # Magic, Color, 52 cartes
    settings = ui.run_menus(SorterSettings(deck="", sort_mode="", card_count=0))
    assert settings.deck == config.DECK_MAGIC
    assert settings.sort_mode == "Color"
    assert settings.card_count == 52
    joined = " ".join(line for pair in lcd.history for line in pair)
    assert "Select deck" in joined
    assert "Select Mode" in joined
    assert "1:C 2:T 3:P 4:R" in joined
    assert "Veuillez entrer" in joined
    assert "carte a traiter." in joined


def test_menu_playing_and_star_clears_count():
    keypad = Keypad(simulate=True)
    lcd = LcdDisplay(simulate=True)
    ui = SorterUI(keypad, lcd)
    keypad.inject("12")      # Jeu 52, Valeur
    keypad.inject("99*12#")  # saisie 99, efface, 12
    settings = ui.run_menus(SorterSettings())
    assert settings.deck == config.DECK_PLAYING
    assert settings.sort_mode == "Rank"
    assert settings.card_count == 12
    joined = " ".join(line for pair in lcd.history for line in pair)
    assert "Nombre efface" in joined
    assert "Jeu 52" in joined


def test_menu_pokemon_default_count_on_hash():
    keypad = Keypad(simulate=True)
    lcd = LcdDisplay(simulate=True)
    ui = SorterUI(keypad, lcd)
    keypad.inject("21#")  # Pokemon, Type, # sans chiffre → défaut 60
    settings = ui.run_menus(SorterSettings())
    assert settings.deck == config.DECK_POKEMON
    assert settings.sort_mode == "Type"
    assert settings.card_count == 60


def test_invalid_sort_then_valid():
    keypad = Keypad(simulate=True)
    lcd = LcdDisplay(simulate=True)
    ui = SorterUI(keypad, lcd)
    keypad.inject("39")  # Magic, touche 9 invalide
    keypad.inject("1")   # Color
    keypad.inject("3#")  # 3 cartes
    settings = ui.run_menus(SorterSettings())
    assert settings.sort_mode == "Color"
    assert settings.card_count == 3
    joined = " ".join(line for pair in lcd.history for line in pair)
    assert "No mode selected" in joined


def test_lcd_print_and_cursor():
    lcd = LcdDisplay(simulate=True)
    lcd.begin(16, 2)
    lcd.set_cursor(0, 0)
    lcd.print("Select Mode")
    lcd.set_cursor(0, 1)
    lcd.print("1:C 2:T 3:P 4:R")
    line1, line2 = lcd.snapshot()
    assert line1.startswith("Select Mode")
    assert line2.startswith("1:C 2:T 3:P 4:R")
    lcd.clear()
    assert lcd.snapshot() == (" " * 16, " " * 16)


def test_arduino_keypad_layout():
    assert KEYMAP == [
        ["1", "2", "3", "A"],
        ["4", "5", "6", "B"],
        ["7", "8", "9", "C"],
        ["*", "0", "#", "D"],
    ]
