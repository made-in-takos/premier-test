"""Tests du driver ULN2003 / 28BYJ-48 (sans GPIO)."""

import config
from arm_controller import FULL4WIRE_SEQUENCE, ArmController


def test_steps_per_revolution_matches_arduino():
    assert config.STEPS_PER_REV == 2048
    assert abs(config.STEPS_PER_DEGREE - 5.689) < 0.002


def test_quarter_turn_is_512_steps():
    arm = ArmController()
    assert arm._angle_to_steps(90) == 512
    assert arm._angle_to_steps(-90) == -512
    assert arm._angle_to_steps(45) == 256
    assert arm._angle_to_steps(1) == 6  # round(5.688…)


def test_full4wire_sequence_has_two_coils_on():
    assert len(FULL4WIRE_SEQUENCE) == 4
    assert all(sum(step) == 2 for step in FULL4WIRE_SEQUENCE)
    assert FULL4WIRE_SEQUENCE[0] == (1, 1, 0, 0)


def test_simulated_move_updates_angle_and_phase():
    original_delay = config.STEP_DELAY_S
    config.STEP_DELAY_S = 0
    try:
        arm = ArmController()
        arm.move_to(90)
        assert arm.current_angle == 90
        assert arm._phase == 512 % 4
        arm.move_to(0)
        assert arm.current_angle == 0
    finally:
        config.STEP_DELAY_S = original_delay
