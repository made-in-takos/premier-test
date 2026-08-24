#!/usr/bin/env python3
"""
Tests materiel GPIO.

    python test_hardware.py status
    python test_hardware.py relays --hold 3
    python test_hardware.py servo-sweep
    python test_hardware.py servo --angle 130
    python test_hardware.py servo-calibrate
    python test_hardware.py card-pick
"""

import argparse
import sys
import time

import config
from gpio_setup import configure_pin_factory

if not config.IS_RASPBERRY:
    print("Ce script doit etre lance sur le Raspberry Pi (GPIO reels).")
    sys.exit(1)

configure_pin_factory()


def cmd_status():
    from gpiozero import Button

    print("=== GPIO (BCM) ===")
    print(f"  STEP         : {config.GPIO_STEP}")
    print(f"  DIR          : {config.GPIO_DIR}")
    print(f"  ENABLE       : {config.GPIO_ENABLE}")
    print(f"  HOME         : {config.GPIO_HOME_SWITCH}")
    print(f"  SERVO        : {config.GPIO_SERVO_TILT}")
    print(f"  POMPE_CARTE  : {config.GPIO_RELAY_PUMP_CARD}")
    print(f"  EV_CARTE     : {config.GPIO_RELAY_VALVE_CARD}")
    print(f"  POMPE_VERIN  : {config.GPIO_RELAY_PUMP_LIFT}")
    print(f"  EV_VERIN     : {config.GPIO_RELAY_VALVE_LIFT}")
    print(f"\n  Servo DOWN={config.SERVO_ANGLE_DOWN}°  UP={config.SERVO_ANGLE_UP}°  (limite {config.SERVO_MIN_ANGLE}–{config.SERVO_MAX_ANGLE}°)")
    print(f"  Relais active_low={config.RELAY_ACTIVE_LOW}  invert={config.RELAY_INVERT_CHANNELS}")
    print("  (comme Arduino : HIGH=ON, vanne piston inversee)")

    sw = Button(config.GPIO_HOME_SWITCH, pull_up=True, bounce_time=0.05)
    state = "ACTIF" if sw.is_pressed else "inactif"
    print(f"\n  Capteur zero : {state}")
    sw.close()


def cmd_relays(hold):
    from gpiozero import DigitalOutputDevice

    active_high = not config.RELAY_ACTIVE_LOW
    channels = [
        ("POMPE_CARTE", config.GPIO_RELAY_PUMP_CARD),
        ("EV_CARTE", config.GPIO_RELAY_VALVE_CARD),
        ("POMPE_VERIN", config.GPIO_RELAY_PUMP_LIFT),
        ("EV_VERIN", config.GPIO_RELAY_VALVE_LIFT),
    ]
    print(f"Chaque relais ON pendant {hold}s (active_high={active_high})…")
    print("Tu dois entendre un clic et voir la LED du module.")
    devices = []
    try:
        for name, pin in channels:
            dev = DigitalOutputDevice(pin, active_high=active_high, initial_value=False)
            devices.append(dev)
            print(f"  {name} GPIO {pin} ON")
            dev.on()
            time.sleep(hold)
            print(f"  {name} OFF")
            dev.off()
            time.sleep(0.4)
    finally:
        for dev in devices:
            dev.off()
            dev.close()
    print("Si rien n'a clique : mets RELAY_ACTIVE_LOW = True dans config.py (module low-trigger).")


def cmd_pins():
    cmd_relays(0.25)


def cmd_step(steps, direction):
    from arm_controller import ArmController

    arm = ArmController()
    try:
        arm.enable_motor(True)
        cw = direction.lower() in ("cw", "horaire", "right", "droite")
        arm._set_direction(cw)
        print(f"{steps} pas ({'horaire' if cw else 'anti-horaire'})…")
        for _ in range(steps):
            arm._pulse_step()
    finally:
        arm.cleanup()


def cmd_home():
    from arm_controller import ArmController

    arm = ArmController()
    try:
        arm.home()
    finally:
        arm.cleanup()


def cmd_move(angle):
    from arm_controller import ArmController

    arm = ArmController()
    try:
        arm.home()
        arm.move_to(angle)
        input("Entree pour retour zero…")
        arm.move_to(config.HOME_ANGLE)
    finally:
        arm.cleanup()


def cmd_scan():
    from arm_controller import ArmController

    arm = ArmController()
    try:
        arm.home()
        for angle in range(int(config.MIN_ANGLE), int(config.MAX_ANGLE) + 1, 15):
            print(f"→ {angle}°")
            arm.move_to(float(angle))
            time.sleep(0.5)
        arm.move_to(config.HOME_ANGLE)
    finally:
        arm.cleanup()


def cmd_servo(angle):
    from servo_controller import ServoController

    servo = ServoController()
    try:
        print(f"Servo → {angle}° (borne {config.SERVO_MIN_ANGLE}–{config.SERVO_MAX_ANGLE})")
        servo.move_to(angle)
        time.sleep(1.5)
    finally:
        servo.cleanup()


def cmd_servo_sweep():
    from servo_controller import ServoController

    servo = ServoController()
    try:
        print(f"Balayage {config.SERVO_MIN_ANGLE}° → {config.SERVO_MAX_ANGLE}° → {config.SERVO_MIN_ANGLE}°")
        servo.move_to(config.SERVO_MIN_ANGLE)
        servo.move_to(config.SERVO_MAX_ANGLE)
        servo.move_to(config.SERVO_ANGLE_UP)
    finally:
        servo.cleanup()


def cmd_servo_calibrate():
    from servo_controller import ServoController

    servo = ServoController()
    try:
        print("Calibration — course limitee 40–130° (Arduino)")
        for angle in (40, 50, 70, 90, 110, 130):
            print(f"\nAngle {angle}° — Entree pour continuer, Q pour quitter")
            servo.move_to(angle)
            if input().strip().lower() == "q":
                break
    finally:
        servo.cleanup()


def cmd_lift_down():
    from pneumatic import PneumaticController

    pneu = PneumaticController()
    try:
        pneu.down()
    finally:
        pneu.cleanup()


def cmd_lift_up():
    from pneumatic import PneumaticController

    pneu = PneumaticController()
    try:
        pneu.up()
    finally:
        pneu.cleanup()


def cmd_card_pick():
    from pneumatic import PneumaticController

    pneu = PneumaticController()
    try:
        pneu.pick()
        input("Aspiration en cours — Entree pour arreter…")
    finally:
        pneu.cleanup()


def cmd_card_release():
    from pneumatic import PneumaticController

    pneu = PneumaticController()
    try:
        pneu.release()
    finally:
        pneu.cleanup()


def cmd_pick_cycle():
    from arm_controller import ArmController
    from pneumatic import PneumaticController
    from servo_controller import ServoController

    arm = ArmController()
    servo = ServoController()
    pneu = PneumaticController()
    try:
        servo.up()
        arm.home()
        arm.move_to(config.PICKUP_ANGLE)
        pneu.to_pickup_height()
        servo.down()
        pneu.pick()
        servo.up()
        pneu.to_transport_height()
        input("Carte aspiree — Entree pour liberer…")
        pneu.to_deposit_height()
        servo.down()
        pneu.release()
        servo.up()
        pneu.to_transport_height()
        arm.move_to(config.HOME_ANGLE)
        print("Cycle termine.")
    finally:
        pneu.cleanup()
        servo.cleanup()
        arm.cleanup()


def main():
    parser = argparse.ArgumentParser(description="Tests GPIO trieur de cartes")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status")
    sub.add_parser("pins")
    sub.add_parser("home")
    sub.add_parser("scan")
    sub.add_parser("servo-calibrate")
    sub.add_parser("servo-sweep")
    sub.add_parser("card-pick")
    sub.add_parser("card-release")
    sub.add_parser("lift-down")
    sub.add_parser("lift-up")
    sub.add_parser("pick-cycle")

    p_relays = sub.add_parser("relays")
    p_relays.add_argument("--hold", type=float, default=3.0)

    p_step = sub.add_parser("step")
    p_step.add_argument("--steps", type=int, default=100)
    p_step.add_argument("--dir", default="cw")

    p_move = sub.add_parser("move")
    p_move.add_argument("--angle", type=float, required=True)

    p_servo = sub.add_parser("servo")
    p_servo.add_argument("--angle", type=float, required=True)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "status": cmd_status,
        "pins": cmd_pins,
        "relays": lambda: cmd_relays(args.hold),
        "home": cmd_home,
        "scan": cmd_scan,
        "servo-calibrate": cmd_servo_calibrate,
        "servo-sweep": cmd_servo_sweep,
        "card-pick": cmd_card_pick,
        "card-release": cmd_card_release,
        "lift-down": cmd_lift_down,
        "lift-up": cmd_lift_up,
        "pick-cycle": cmd_pick_cycle,
        "step": lambda: cmd_step(args.steps, args.dir),
        "move": lambda: cmd_move(args.angle),
        "servo": lambda: cmd_servo(args.angle),
    }
    commands[args.command]()


if __name__ == "__main__":
    main()
