"""Test servo : mapping 0–180° et monter / descendre."""

import config
from servo_controller import ServoController, angle_to_pulse_us, command_pulse_us


def test_write_n_est_proportionnel_a_n_degres():
    assert config.SERVO_MIN_PULSE_US == 1000
    assert config.SERVO_MAX_PULSE_US == 2000
    assert angle_to_pulse_us(0) == 1000
    assert angle_to_pulse_us(180) == 2000
    assert abs(angle_to_pulse_us(90) - 1500) < 1
    assert abs(angle_to_pulse_us(50) - 1278) < 1
    assert abs(angle_to_pulse_us(130) - 1722) < 1


def test_invert_echange_les_butées():
    original = config.SERVO_INVERT
    try:
        config.SERVO_INVERT = False
        assert abs(command_pulse_us(50) - angle_to_pulse_us(50)) < 1
        config.SERVO_INVERT = True
        assert abs(command_pulse_us(50) - angle_to_pulse_us(130)) < 1
        assert abs(command_pulse_us(0) - angle_to_pulse_us(180)) < 1
    finally:
        config.SERVO_INVERT = original


def test_monter_descendre_monter_descendre():
    servo = ServoController()
    assert servo.current_angle == config.SERVO_ANGLE_DOWN

    servo.up()
    assert servo.current_angle == config.SERVO_ANGLE_UP
    servo.down()
    assert servo.current_angle == config.SERVO_ANGLE_DOWN
    servo.up()
    assert servo.current_angle == config.SERVO_ANGLE_UP
    servo.down()
    assert servo.current_angle == config.SERVO_ANGLE_DOWN

    servo.cleanup()
    assert servo.measured_hz == 0.0
