"""Tests de la polarité des relais."""

import config
from pneumatic import PneumaticController, gpio_high_for


def test_default_is_active_low_for_pi_3v3():
    assert config.RELAY_ACTIVE_LOW is True
    assert gpio_high_for(True) is False
    assert gpio_high_for(False) is True


def test_gpio_high_for_respects_polarity():
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


def test_each_runs_in_simulation():
    pneu = PneumaticController()
    pneu.test_each(hold_s=0)
    pneu.cleanup()
