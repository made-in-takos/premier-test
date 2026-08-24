from servo_math import clamp_servo_angle, servo_sweep


def test_clamp_keeps_arduino_range():
    assert clamp_servo_angle(0, 40, 130) == 40
    assert clamp_servo_angle(180, 40, 130) == 130
    assert clamp_servo_angle(90, 40, 130) == 90
    assert clamp_servo_angle(40.4, 40, 130) == 40


def test_sweep_matches_arduino_fct():
    assert servo_sweep(40, 43) == [40, 41, 42, 43]
    assert servo_sweep(130, 128) == [130, 129, 128]
    assert servo_sweep(90, 90) == [90]
