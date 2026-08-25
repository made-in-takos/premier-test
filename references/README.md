# Images de référence (rang + couleur)

Ce dossier doit contenir **tes** photos de symboles, pas des images génériques.

```
references/ranks/Ace.jpg ... King.jpg
references/suits/Spades.jpg Hearts.jpg Clubs.jpg Diamonds.jpg
```

Même jeu, même éclairage, fond sombre, coin haut-gauche bien visible.

```bash
source .venv/bin/activate
python vision/capture_references.py --rank Ace
# barre d'espace pour enregistrer, q pour quitter
python vision/capture_references.py --suit Hearts
```

Les 13 rangs : `Ace 2 3 4 5 6 7 8 9 10 Jack Queen King`  
Les 4 couleurs : `Spades Hearts Clubs Diamonds`
