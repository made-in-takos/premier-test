"""
Tables de tri — portage de FCTTriParCouleur / modes Arduino,
plus les variantes Jeu 52 et Pokémon.
"""

import config

# ---------------------------------------------------------------------------
# Types de cartes (nouveau menu, même principe que Select Mode)
# ---------------------------------------------------------------------------

DECK_OPTIONS = (
    (config.DECK_PLAYING, "1", "Jeu 52"),
    (config.DECK_POKEMON, "2", "Pokemon"),
    (config.DECK_MAGIC, "3", "Magic"),
)

DECK_FROM_KEY = {key: deck_id for deck_id, key, _label in DECK_OPTIONS}
DECK_LABEL = {deck_id: label for deck_id, _key, label in DECK_OPTIONS}

# Modes de tri par type de jeu — Magic = sketch Arduino (1:C 2:T 3:P 4:R)
SORT_OPTIONS = {
    config.DECK_MAGIC: (
        ("Color", "1", "Color"),
        ("Type", "2", "Type"),
        ("Cost", "3", "Cost"),
        ("Rarity", "4", "Rarity"),
    ),
    config.DECK_PLAYING: (
        ("Color", "1", "Couleur"),
        ("Rank", "2", "Valeur"),
        ("RedBlack", "3", "Rouge/Noir"),
    ),
    config.DECK_POKEMON: (
        ("Type", "1", "Type"),
        ("Category", "2", "Categorie"),
        ("Rarity", "3", "Rarity"),
    ),
}

DEFAULT_COUNT = {
    config.DECK_PLAYING: 52,
    config.DECK_POKEMON: 60,
    config.DECK_MAGIC: 60,
}

# Alias anglais → noms français du enum Arduino
MAGIC_COLOR_ALIASES = {
    "Red": "Rouge",
    "Blue": "Bleu",
    "Green": "Vert",
    "White": "Blanc",
    "Black": "Noir",
}

# FCTTriParCouleur : Angle = 18 * facteur
MAGIC_COLOR_FACTORS = {
    "Rouge": -1,
    "Bleu": -2,
    "Vert": -3,
    "Blanc": -4,
    "Noir": -5,
    "Azorius": -6,
    "Boros": -7,
    "Dimir": -8,
    "Golgari": -9,
    "Gruul": -10,
    "Izzet": 1,
    "Orzhov": 2,
    "Rakdos": 3,
    "Selesnya": 4,
    "Simic": 5,
    "Abzan": 6,
    "Bant": 7,
    "Esper": 8,
    "Grixis": 9,
    "Jeskai": -1,
    "Jund": -1,
    "Mardu": -2,
    "Naya": -3,
    "Sultai": -4,
    "Temur": -5,
    "Glint": -6,
    "Dune": -7,
    "Ink": -8,
    "Witch": -9,
    "Yore": -10,
    "WUBRG": 9,
    "Colorless": 1,
}

MAGIC_TYPE_FACTORS = {
    "Creature": -1,
    "Instant": -2,
    "Sorcery": -3,
    "Enchantment": -4,
    "Artifact": 1,
    "Land": 2,
    "Planeswalker": 3,
    "Other": 4,
}

MAGIC_COST_FACTORS = {
    "0": -1,
    "1": -2,
    "2": -3,
    "3": 1,
    "4": 2,
    "5+": 3,
}

MAGIC_RARITY_FACTORS = {
    "Common": -2,
    "Uncommon": -1,
    "Rare": 1,
    "Mythic": 2,
}

POKEMON_TYPE_FACTORS = {
    "Fire": -1,
    "Water": -2,
    "Grass": -3,
    "Lightning": -4,
    "Psychic": -5,
    "Fighting": 1,
    "Darkness": 2,
    "Metal": 3,
    "Fairy": 4,
    "Dragon": 5,
    "Colorless": 6,
}

POKEMON_CATEGORY_FACTORS = {
    "Pokemon": -2,
    "Trainer": 1,
    "Energy": 2,
}

POKEMON_RARITY_FACTORS = {
    "Common": -2,
    "Uncommon": -1,
    "Rare": 1,
    "Ultra": 2,
}

PLAYING_RANK_GROUPS = {
    "Ace": 0,
    "2": 0,
    "3": 0,
    "4": 1,
    "5": 1,
    "6": 1,
    "7": 1,
    "8": 2,
    "9": 2,
    "10": 2,
    "Jack": 3,
    "Queen": 3,
    "King": 3,
}

PLAYING_RANK_BINS = [-75.0, -50.0, 50.0, 75.0]

RED_SUITS = {"Hearts", "Diamonds", "Coeur", "Carreau"}
BLACK_SUITS = {"Clubs", "Spades", "Trefle", "Pique"}


def sort_mode_from_key(deck_id, key):
    for mode_id, mode_key, _label in SORT_OPTIONS.get(deck_id, ()):
        if mode_key == key:
            return mode_id
    return None


def sort_label(deck_id, mode_id):
    for current_id, _key, label in SORT_OPTIONS.get(deck_id, ()):
        if current_id == mode_id:
            return label
    return mode_id or ""


def lcd_sort_line(deck_id):
    """Deuxième ligne LCD, style Arduino '1:C 2:T 3:P 4:R'."""
    if deck_id == config.DECK_MAGIC:
        return "1:C 2:T 3:P 4:R"
    if deck_id == config.DECK_PLAYING:
        return "1:Coul 2:Val 3:RN"
    if deck_id == config.DECK_POKEMON:
        return "1:Typ 2:Cat 3:Rar"
    return ""


def normalize_magic_color(name):
    if not name:
        return None
    name = str(name).strip()
    return MAGIC_COLOR_ALIASES.get(name, name)


def magic_color_angle(color_name):
    """Portage de FCTTriParCouleur. NotFound → 0°."""
    color = normalize_magic_color(color_name)
    if color not in MAGIC_COLOR_FACTORS:
        return config.HOME_ANGLE
    return config.MAGIC_ANGLE_STEP * MAGIC_COLOR_FACTORS[color]


def _factor_angle(table, key):
    if key is None or key not in table:
        return config.HOME_ANGLE
    return config.MAGIC_ANGLE_STEP * table[key]


def playing_drop_angle(sort_mode, result):
    if not result:
        return config.HOME_ANGLE
    suit = result.get("suit")
    rank = result.get("rank")
    if sort_mode == "Color":
        return config.SORT_ANGLES.get(suit, config.HOME_ANGLE)
    if sort_mode == "RedBlack":
        if suit in RED_SUITS:
            return config.SORT_ANGLES["Hearts"]
        if suit in BLACK_SUITS:
            return config.SORT_ANGLES["Spades"]
        return config.HOME_ANGLE
    if sort_mode == "Rank":
        index = PLAYING_RANK_GROUPS.get(rank)
        if index is None:
            return config.HOME_ANGLE
        return PLAYING_RANK_BINS[index]
    return config.HOME_ANGLE


def drop_angle(deck_id, sort_mode, result):
    """Angle de dépôt selon le type de jeu et le mode de tri."""
    if not result:
        return config.HOME_ANGLE

    if deck_id == config.DECK_PLAYING:
        return playing_drop_angle(sort_mode, result)

    if deck_id == config.DECK_MAGIC:
        if sort_mode == "Color":
            return magic_color_angle(result.get("color") or result.get("suit"))
        if sort_mode == "Type":
            return _factor_angle(MAGIC_TYPE_FACTORS, result.get("type"))
        if sort_mode == "Cost":
            cost = result.get("cost")
            if cost is not None:
                try:
                    value = int(cost)
                    cost = "5+" if value >= 5 else str(value)
                except (TypeError, ValueError):
                    cost = str(cost)
            return _factor_angle(MAGIC_COST_FACTORS, cost)
        if sort_mode == "Rarity":
            return _factor_angle(MAGIC_RARITY_FACTORS, result.get("rarity"))
        return config.HOME_ANGLE

    if deck_id == config.DECK_POKEMON:
        if sort_mode == "Type":
            return _factor_angle(POKEMON_TYPE_FACTORS, result.get("type") or result.get("color"))
        if sort_mode == "Category":
            return _factor_angle(POKEMON_CATEGORY_FACTORS, result.get("category"))
        if sort_mode == "Rarity":
            return _factor_angle(POKEMON_RARITY_FACTORS, result.get("rarity"))
        return config.HOME_ANGLE

    return config.HOME_ANGLE


def result_label(deck_id, result):
    if not result:
        return "Inconnue"
    if deck_id == config.DECK_PLAYING:
        rank = result.get("rank", "?")
        suit = result.get("suit", "?")
        return f"{rank} {suit}"
    if deck_id == config.DECK_MAGIC:
        return str(
            result.get("color")
            or result.get("type")
            or result.get("name")
            or "Magic"
        )
    if deck_id == config.DECK_POKEMON:
        return str(result.get("name") or result.get("type") or "Pokemon")
    return "Carte"
