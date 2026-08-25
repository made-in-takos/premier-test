"""Tests de la polarité des relais."""

import config
from pneumatic import gpio_high_for


def test_arduino_active_high_by_default():
    original = config.RELAY_ACTIVE_LOW
    try:
        config.RELAY_ACTIVE_LOW = False
        assert gpio_high_for(True) is True
        assert gpio_high_for(False) is False
        config.RELAY_ACTIVE_LOW = True
        assert gpio_high_for(True) is False
        assert gpio_high_for(False) is True
    finally:
        config.RELAY_ACTIVE_LOW = original
