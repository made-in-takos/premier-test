"""Backend GPIO pour Raspberry Pi 5 (lgpio, pas RPi.GPIO / pigpio)."""

from __future__ import annotations

import config

_configured = False


def configure_pin_factory() -> str:
    """Force lgpio sur Pi 5. RPi.GPIO et pigpio n'y commandent pas les GPIO."""
    global _configured
    if _configured:
        return "already"
    _configured = True
    if not config.IS_RASPBERRY:
        return "simulation"
    try:
        from gpiozero import Device
        from gpiozero.pins.lgpio import LGPIOFactory

        Device.pin_factory = LGPIOFactory()
        return "lgpio"
    except Exception as exc:  # noqa: BLE001
        print(
            f"[GPIO] lgpio indisponible ({exc}). "
            "Sur un Pi 5 : sudo apt install python3-lgpio python3-gpiozero"
        )
        return "fallback"
