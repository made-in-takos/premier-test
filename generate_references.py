"""
Génère les images de référence pour la reconnaissance OpenCV.

Modes d'utilisation :
  python generate_references.py              # mode guidé + fenêtre vidéo
  python generate_references.py --web        # flux dans le navigateur (SSH)
  python generate_references.py --preview  # test live sans sauvegarder
  python generate_references.py --rank Ace --suit Hearts
  python generate_references.py --force      # écrase les fichiers existants

Contrôles :
  ESPACE  → capturer et sauvegarder
  S       → passer
  Q       → quitter
"""

import argparse
import os
import sys

import cv2

from camera import Camera
from card_recognition import REF_RANK_DIR, REF_SUIT_DIR, RANKS, SUITS
from video_preview import VideoPreview, build_preview_frame, detect_card_in_frame


def ensure_dirs():
    os.makedirs(REF_RANK_DIR, exist_ok=True)
    os.makedirs(REF_SUIT_DIR, exist_ok=True)


def ref_path(name, folder):
    return os.path.join(folder, f"{name}.jpg")


def ref_exists(name, folder):
    return os.path.exists(ref_path(name, folder))


def save_reference(name, image, folder):
    path = ref_path(name, folder)
    cv2.imwrite(path, image)
    print(f"  Sauvegardé : {path}")
    return path


def wait_for_capture(preview, cam, label, save_rank=None, save_suit=None, force=False):
    if save_rank and ref_exists(save_rank, REF_RANK_DIR) and not force:
        print(f"  Déjà présent : {save_rank}.jpg (S pour passer)")
    if save_suit and ref_exists(save_suit, REF_SUIT_DIR) and not force:
        print(f"  Déjà présent : {save_suit}.jpg (S pour passer)")

    while True:
        frame = cam.capture()
        if frame is None:
            continue

        detected = detect_card_in_frame(frame)
        view = build_preview_frame(frame, detected, title=label)
        preview.show(view)

        if preview.use_gui:
            key = cv2.waitKey(1) & 0xFF
        else:
            key = 0
            try:
                import select
                import tty
                import termios

                fd = sys.stdin.fileno()
                old = termios.tcgetattr(fd)
                try:
                    tty.setraw(fd)
                    if select.select([sys.stdin], [], [], 0)[0]:
                        key = ord(sys.stdin.read(1))
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old)
            except ImportError:
                pass

        if key in (ord("q"), ord("Q")):
            return "quit"
        if key in (ord("s"), ord("S")):
            print("  Passé.")
            return "skip"
        if key == 32:
            if detected is None:
                print("  Aucune carte détectée — réessaie.")
                continue
            if save_rank:
                save_reference(save_rank, detected["rank_img"], REF_RANK_DIR)
            if save_suit:
                save_reference(save_suit, detected["suit_img"], REF_SUIT_DIR)
            print("  Capture OK !")
            return "saved"


def print_inventory():
    rank_done = sum(1 for r in RANKS if ref_exists(r, REF_RANK_DIR))
    suit_done = sum(1 for s in SUITS if ref_exists(s, REF_SUIT_DIR))
    print(f"\nInventaire : {rank_done}/13 rangs, {suit_done}/4 couleurs")
    missing_ranks = [r for r in RANKS if not ref_exists(r, REF_RANK_DIR)]
    missing_suits = [s for s in SUITS if not ref_exists(s, REF_SUIT_DIR)]
    if missing_ranks:
        print(f"  Rangs manquants     : {', '.join(missing_ranks)}")
    if missing_suits:
        print(f"  Couleurs manquantes : {', '.join(missing_suits)}")
    print()


def run_interactive(preview, cam, capture_ranks=True, capture_suits=True, force=False):
    print_inventory()

    if capture_ranks:
        print("=== CAPTURE DES RANGS (13 cartes) ===")
        print("N'importe quelle couleur convient pour chaque rang.\n")
        for rank in RANKS:
            if ref_exists(rank, REF_RANK_DIR) and not force:
                print(f"[{rank}] déjà capturé — S pour passer")
            else:
                print(f"\n>>> Place une carte : {rank}")
            result = wait_for_capture(preview, cam, f"Rang : {rank}", save_rank=rank, force=force)
            if result == "quit":
                return

    if capture_suits:
        print("\n=== CAPTURE DES COULEURS (4 cartes) ===")
        print("N'importe quel rang convient pour chaque couleur.\n")
        for suit in SUITS:
            if ref_exists(suit, REF_SUIT_DIR) and not force:
                print(f"[{suit}] déjà capturé — S pour passer")
            else:
                print(f"\n>>> Place une carte : {suit}")
            result = wait_for_capture(preview, cam, f"Couleur : {suit}", save_suit=suit, force=force)
            if result == "quit":
                return

    print("\n=== Terminé ===")
    print_inventory()


def run_preview_loop(preview, cam):
    print("Mode preview — Q pour quitter.")
    while True:
        frame = cam.capture()
        if frame is None:
            continue
        detected = detect_card_in_frame(frame)
        view = build_preview_frame(frame, detected, title="Preview", hints="Q=quitter")
        preview.show(view)
        if preview.use_gui and (cv2.waitKey(1) & 0xFF) in (ord("q"), ord("Q")):
            break


def main():
    parser = argparse.ArgumentParser(description="Capture guidée avec retour vidéo")
    parser.add_argument("--rank", choices=RANKS)
    parser.add_argument("--suit", choices=SUITS)
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--ranks-only", action="store_true")
    parser.add_argument("--suits-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--web", action="store_true", help="Flux vidéo dans le navigateur (SSH)")
    parser.add_argument("--no-gui", action="store_true", help="Désactiver la fenêtre OpenCV")
    args = parser.parse_args()

    ensure_dirs()
    preview = VideoPreview(use_gui=not args.no_gui, use_web=args.web)
    cam = Camera()

    try:
        if args.preview:
            run_preview_loop(preview, cam)
            return

        if args.rank or args.suit:
            parts = []
            if args.rank:
                parts.append(f"Rang {args.rank}")
            if args.suit:
                parts.append(f"Couleur {args.suit}")
            wait_for_capture(
                preview, cam, " | ".join(parts),
                save_rank=args.rank, save_suit=args.suit, force=args.force,
            )
            return

        run_interactive(
            preview, cam,
            capture_ranks=not args.suits_only,
            capture_suits=not args.ranks_only,
            force=args.force,
        )
    finally:
        cam.cleanup()
        preview.close()


if __name__ == "__main__":
    main()
