"""Polarite relais, alignee sur le sketch Arduino."""

from __future__ import annotations


def requested_on(channel: str, state: bool, invert_channels: tuple[str, ...]) -> bool:
    """True si le relais doit etre active electriquement."""
    if channel in invert_channels:
        return not state
    return bool(state)
