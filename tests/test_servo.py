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


def test_simulated_move_updates_angle():
    original = config.SERVO_MS_PER_DEG
    config.SERVO_MS_PER_DEG = 0
    try:
        servo = ServoController()
        assert servo.backend == "sim"
        servo.move_to(25)
        assert servo.current_angle == 25
        servo.up()
        assert servo.current_angle == config.SERVO_ANGLE_UP
        servo.cleanup()
    finally:
        config.SERVO_MS_PER_DEG = original
