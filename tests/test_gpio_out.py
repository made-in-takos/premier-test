"""BCM → pin physique du header 40 broches."""

from gpio_out import describe, physical


def test_servo_bcm18_is_header_pin_12_not_18():
    assert physical(18) == 12
    assert "12" in describe(18)


def test_relay1_bcm24_is_header_pin_18():
    assert physical(24) == 18
    assert "18" in describe(24)


def test_stepper_in1_next_to_servo():
    assert physical(17) == 11
    assert physical(18) == 12
