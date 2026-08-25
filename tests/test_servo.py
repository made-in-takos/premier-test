"""Test servo : impulsions Arduino + monter / descendre."""

import config
from servo_controller import ServoController, angle_to_pulse_us


def test_impulsions_identiques_servo_h():
    assert angle_to_pulse_us(0) == config.SERVO_MIN_PULSE_US
    assert angle_to_pulse_us(180) == config.SERVO_MAX_PULSE_US
    assert abs(angle_to_pulse_us(90) - 1472) < 1
    assert abs(angle_to_pulse_us(50) - 1060) < 1
    assert abs(angle_to_pulse_us(130) - 1884) < 1
    # write(50) n'est pas 50 % de la course 1000–2000 µs d'un SG90
    assert angle_to_pulse_us(50) < 1200


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
