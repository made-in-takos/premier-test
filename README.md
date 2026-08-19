# Trieur de cartes — Raspberry Pi 5

Menus sur **pavé 4×4** + **LCD 16×2** (portage du sketch Arduino), reconnaissance OpenCV pour le jeu de 52, tri Magic / Pokémon préparé.

## Lancement

```bash
bash setup_pi.sh
source venv/bin/activate
python main.py
```

Sans menus (ligne de commande) :

```bash
python main.py --skip-menu --skip-test --deck playing --sort Color --count 52
python main.py --deck magic --sort Color --count 10 --skip-test
```

## Menus (pavé)

Même logique que l’Arduino : `#` valide, `*` efface.

1. **Mise à zéro** — `Start pos ok ?`  
   `1/2` ±1°, `4/5` ±5°, `7/8` ±20°, `#` mémorise le zéro
2. **En test** — `1` servo, `2` rotation, `3` relais, `#` suite
3. **Type de cartes** — `1:52  2:Pkm  3:Mag`
4. **Mode de tri**
   - Magic : `1:C 2:T 3:P 4:R` (Color, Type, Cost, Rarity)
   - Jeu 52 : couleur / valeur / rouge-noir
   - Pokémon : type / catégorie / rareté
5. **Nombre de cartes** — chiffres puis `#` (`*` pour effacer)

Pendant le tri, `*` ou `C` demande l’arrêt.

## Câblage

Les broches Mega du sketch (`50,48,46…` et `LiquidCrystal(22,24,26,28,30,32)`) sont reportées en BCM dans `config.py`. Détail : **[BRANCHEMENTS.md](BRANCHEMENTS.md)**.

## Tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest tests
python test_hardware.py lcd
python test_hardware.py keypad
```
