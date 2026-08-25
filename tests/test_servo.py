"""Tests du mapping angle → impulsion servo (sans GPIO)."""

import config
from servo_controller import ServoController, angle_to_pulse_us, pulse_us_to_duty


def test_pulse_at_endpoints_and_mid():
    assert angle_to_pulse_us(0) == config.SERVO_MIN_PULSE_US
    assert angle_to_pulse_us(180) == config.SERVO_MAX_PULSE_US
    assert angle_to_pulse_us(90) == (
        config.SERVO_MIN_PULSE_US + config.SERVO_MAX_PULSE_US
    ) / 2
    assert angle_to_pulse_us(-10) == config.SERVO_MIN_PULSE_US
    assert angle_to_pulse_us(200) == config.SERVO_MAX_PULSE_US


def test_duty_cycle_50hz():
    # 1500 µs dans une trame 20 ms = 7,5 %
    assert abs(pulse_us_to_duty(1500, 50) - 7.5) < 0.01
    assert pulse_us_to_duty(0, 50) == 0
    assert pulse_us_to_duty(20000, 50) == 100


def test_invert_swaps_pulse_direction():
    original = config.SERVO_INVERT
    try:
        config.SERVO_INVERT = False
        normal_up = angle_to_pulse_us(config.SERVO_ANGLE_UP)
        config.SERVO_INVERT = True
        inverted_up = angle_to_pulse_us(config.SERVO_ANGLE_UP)
        assert inverted_up != normal_up
        assert abs(
            (normal_up + inverted_up)
            - (config.SERVO_MIN_PULSE_US + config.SERVO_MAX_PULSE_US)
        ) < 1
    finally:
        config.SERVO_INVERT = original


def test_simulated_move_updates_angle():
    original = config.SERVO_MS_PER_DEG
    config.SERVO_MS_PER_DEG = 0
    try:
        servo = ServoController()
        assert servo.backend == "sim"
        assert servo.current_angle == config.SERVO_ANGLE_DOWN
        servo.move_to(25)
        assert servo.current_angle == 25
        servo.up()
        assert servo.current_angle == config.SERVO_ANGLE_UP
        servo.down()
        assert servo.current_angle == config.SERVO_ANGLE_DOWN
        servo.cleanup()
    finally:
        config.SERVO_MS_PER_DEG = original
