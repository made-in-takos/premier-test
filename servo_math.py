"""Bornes d'angle servo (course Arduino 40–130°)."""

from __future__ import annotations


def clamp_servo_angle(angle: float, min_angle: float, max_angle: float) -> int:
    """Limite l'angle a la course mecanique, en degres entiers."""
    if min_angle > max_angle:
        min_angle, max_angle = max_angle, min_angle
    bounded = max(min_angle, min(max_angle, angle))
    return int(round(bounded))


def servo_sweep(start: int, target: int) -> list[int]:
    """Liste des angles intermediaires, 1° par 1° comme FCTControlleServo."""
    if start == target:
        return [target]
    step = 1 if target > start else -1
    return list(range(start, target + step, step))
