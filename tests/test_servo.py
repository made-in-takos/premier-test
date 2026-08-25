"""Test servo : impulsions Arduino + monter / descendre."""

import config
from servo_controller import ServoController, angle_to_pulse_us


def test_impulsions_identiques_servo_h():
    assert angle_to_pulse_us(0) == 544
    assert angle_to_pulse_us(180) == 2400
    assert abs(angle_to_pulse_us(90) - 1472) < 1
    assert abs(angle_to_pulse_us(50) - 1060) < 1
    assert abs(angle_to_pulse_us(130) - 1884) < 1


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
