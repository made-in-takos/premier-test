from servo_math import clamp_servo_angle, servo_sweep
from relay_math import requested_on


def test_clamp_keeps_arduino_range():
    assert clamp_servo_angle(0, 40, 130) == 40
    assert clamp_servo_angle(180, 40, 130) == 130
    assert clamp_servo_angle(90, 40, 130) == 90
    assert clamp_servo_angle(40.4, 40, 130) == 40


def test_sweep_matches_arduino_fct():
    assert servo_sweep(40, 43) == [40, 41, 42, 43]
    assert servo_sweep(130, 128) == [130, 129, 128]
    assert servo_sweep(90, 90) == [90]


def test_piston_valve_is_inverted_like_arduino():
    invert = ("valve_lift",)
    assert requested_on("pump_card", True, invert) is True
    assert requested_on("pump_card", False, invert) is False
    assert requested_on("valve_lift", True, invert) is False
    assert requested_on("valve_lift", False, invert) is True
