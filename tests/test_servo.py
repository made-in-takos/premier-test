"""Test servo : monter, descendre, monter, descendre."""

import config
from servo_controller import ServoController


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
