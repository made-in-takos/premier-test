#!/usr/bin/env python3
"""
Tests matériel GPIO — valide chaque composant avant main.py.

Usage :
    python test_hardware.py status
    python test_hardware.py pins
    python test_hardware.py step --steps 512 --dir cw
    python test_hardware.py home
    python test_hardware.py move --angle -45
    python test_hardware.py scan
    python test_hardware.py servo --angle 45
    python test_hardware.py servo-sweep
    python test_hardware.py servo-calibrate
    python test_hardware.py card-pick
    python test_hardware.py card-release
    python test_hardware.py relays
    python test_hardware.py blink --bcm 24
    python test_hardware.py pick-cycle
    python test_hardware.py lcd
    python test_hardware.py keypad
"""

import argparse
import sys
import time

import config

if not config.IS_RASPBERRY:
    print("Ce script doit être lancé sur le Raspberry Pi (GPIO réels).")
    sys.exit(1)


def cmd_status():
    from gpiozero import Button
    from gpio_out import describe

    print("=== GPIO : BCM = pin physique du header 40 broches ===")
    print("  (le stepper qui marche est sur pin 11 ; le servo doit être sur pin 12)")
    print(f"  ULN2003 IN1  : {describe(config.GPIO_STEPPER_IN1)}")
    print(f"  ULN2003 IN2  : {describe(config.GPIO_STEPPER_IN2)}")
    print(f"  ULN2003 IN3  : {describe(config.GPIO_STEPPER_IN3)}")
    print(f"  ULN2003 IN4  : {describe(config.GPIO_STEPPER_IN4)}")
    print(f"  HOME         : {describe(config.GPIO_HOME_SWITCH)}")
    print(f"  SERVO        : {describe(config.GPIO_SERVO_TILT)}  ← pas la pin 18 BOARD")
    print(f"  POMPE_CARTE  : {describe(config.GPIO_RELAY_PUMP_CARD)}")
    print(f"  EV_CARTE     : {describe(config.GPIO_RELAY_VALVE_CARD)}")
    print(f"  POMPE_VERIN  : {describe(config.GPIO_RELAY_PUMP_LIFT)}")
    print(f"  EV_VERIN     : {describe(config.GPIO_RELAY_VALVE_LIFT)}")
    print(f"  LCD RS/E/D4-7: {config.LCD_RS}/{config.LCD_E}/{config.LCD_DATA_PINS}")
    print(f"  KEYPAD ROWS  : {config.KEYPAD_ROW_PINS}")
    print(f"  KEYPAD COLS  : {config.KEYPAD_COL_PINS}")
    print(f"\n  Servo UP={config.SERVO_ANGLE_UP}°  DOWN={config.SERVO_ANGLE_DOWN}°")
    print(f"  Relais ON = GPIO {'LOW 0 V' if config.RELAY_ACTIVE_LOW else 'HIGH 3,3 V'}")
    print(f"  Rotation {config.MIN_ANGLE}° à {config.MAX_ANGLE}°")
    print(f"  28BYJ-48 / ULN2003 : {config.STEPS_PER_REV} pas/tour")

    sw = Button(config.GPIO_HOME_SWITCH, pull_up=True, bounce_time=0.05)
    state = "ACTIF" if sw.is_pressed else "inactif"
    print(f"\n  Capteur zéro : {state}")
    sw.close()


def cmd_pins():
    from gpiozero import Button
    from gpio_out import describe, digital_output

    outputs = {
        "ULN2003_IN1": config.GPIO_STEPPER_IN1,
        "ULN2003_IN2": config.GPIO_STEPPER_IN2,
        "ULN2003_IN3": config.GPIO_STEPPER_IN3,
        "ULN2003_IN4": config.GPIO_STEPPER_IN4,
        "SERVO": config.GPIO_SERVO_TILT,
        "POMPE_CARTE": config.GPIO_RELAY_PUMP_CARD,
        "EV_CARTE": config.GPIO_RELAY_VALVE_CARD,
        "POMPE_VERIN": config.GPIO_RELAY_PUMP_LIFT,
        "EV_VERIN": config.GPIO_RELAY_VALVE_LIFT,
    }
    devices = {}

    print("=== Clignotement GPIO HIGH/LOW (5× chacun, même driver que le stepper) ===")
    try:
        for name, pin in outputs.items():
            dev = digital_output(pin, initial_high=False)
            devices[name] = dev
            print(f"  {name}  {describe(pin)}…")
            for _ in range(5):
                dev.on()
                time.sleep(0.25)
                dev.off()
                time.sleep(0.25)

        sw = Button(config.GPIO_HOME_SWITCH, pull_up=True, bounce_time=0.05)
        print("\nCapteur zéro — actionne le switch (10 s)…")
        t0 = time.time()
        while time.time() - t0 < 10:
            if sw.is_pressed:
                print("  → Détecté !")
            time.sleep(0.1)
        sw.close()
    finally:
        for dev in devices.values():
            dev.off()
            dev.close()


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
        input("Entrée pour retour zéro…")
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
        print(f"Servo.write({angle})")
        servo.move_to(angle)
        input("Entrée pour arrêter…")
    finally:
        servo.cleanup(park=False)


def cmd_servo_calibrate():
    from servo_controller import ServoController

    servo = ServoController()
    try:
        print("Calibration — note SERVO_ANGLE_UP / SERVO_ANGLE_DOWN dans config.py")
        for angle in (0, 25, 50, 90, 130, 160, 180):
            print(f"\nwrite({angle}) — Entrée pour continuer, Q pour quitter")
            servo.move_to(angle)
            if input().strip().lower() == "q":
                break
    finally:
        servo.cleanup()


def cmd_servo_sweep():
    from gpio_out import describe
    from servo_controller import ServoController

    print(f"Signal servo → {describe(config.GPIO_SERVO_TILT)}")
    print("PWM 50 Hz, 544–2400 µs (Servo.h). 50° ≈ 1060 µs, 130° ≈ 1884 µs.")
    print("Un aller 50↔130 doit prendre ~3 s. Si le sens est faux, inverse UP/DOWN.")
    servo = ServoController()
    try:
        print("monter, descendre, monter, descendre")
        servo.up()
        servo.down()
        servo.up()
        servo.down()
        print("Test terminé.")
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
        input("Aspiration en cours — Entrée pour arrêter…")
    finally:
        pneu.cleanup()


def cmd_card_release():
    from pneumatic import PneumaticController

    pneu = PneumaticController()
    try:
        pneu.release()
    finally:
        pneu.cleanup()


def cmd_relays():
    from pneumatic import PneumaticController

    print("Chaque entrée IN : HIGH 3,3 V pendant 2 s, puis LOW 0 V pendant 2 s.")
    print("Regarde les LED IN du module (pas seulement le 5 V d'alimentation).")
    print("  LED allumée seulement en LOW  → trigger LOW (déjà RELAY_ACTIVE_LOW = True)")
    print("  LED allumée seulement en HIGH → mets RELAY_ACTIVE_LOW = False dans config.py")
    print("  LED jamais allumée            → mauvais pin physique, ou 3,3 V trop faible")
    pneu = PneumaticController()
    try:
        pneu.test_each()
    finally:
        pneu.cleanup()


def cmd_blink(bcm):
    from gpio_out import blink, describe

    print(f"Même driver gpiozero que le stepper qui marche — {describe(bcm)}")
    print("Si rien ne bouge : ce n'est pas le pin physique indiqué, ou le 3,3 V ne passe pas.")
    blink(bcm)


def cmd_pick_cycle():
    """Test complet : rotation → descente → aspiration → remontée."""
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
        input("Carte aspirée — Entrée pour libérer…")
        pneu.to_deposit_height()
        servo.down()
        pneu.release()
        servo.up()
        pneu.to_transport_height()
        arm.move_to(config.HOME_ANGLE)
        print("Cycle terminé.")
    finally:
        pneu.cleanup()
        servo.cleanup()
        arm.cleanup()


def cmd_lcd():
    from lcd_display import LcdDisplay

    lcd = LcdDisplay()
    try:
        lcd.begin(16, 2)
        lcd.message("LCD OK", "Hello Carte")
        print("Message affiché 5 s…")
        time.sleep(5)
        lcd.message("Ligne 1 16 car.", "Ligne 2 16 car.")
        time.sleep(3)
        lcd.clear()
    finally:
        lcd.cleanup()


def cmd_keypad():
    from keypad import Keypad
    from lcd_display import LcdDisplay

    pad = Keypad()
    lcd = LcdDisplay()
    try:
        lcd.begin(16, 2)
        lcd.message("Touche une key", "# quitte")
        print("Appuie sur le pavé — # pour quitter (30 s max).")
        t0 = time.time()
        while time.time() - t0 < 30:
            key = pad.get_key()
            if not key:
                time.sleep(0.05)
                continue
            print(f"  touche : {key}")
            lcd.message("Touche :", key)
            if key == "#":
                break
    finally:
        pad.cleanup()
        lcd.cleanup()


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
    sub.add_parser("relays")
    sub.add_parser("lift-down")
    sub.add_parser("lift-up")
    sub.add_parser("pick-cycle")

    p_step = sub.add_parser("step")
    p_step.add_argument("--steps", type=int, default=512)
    p_step.add_argument("--dir", default="cw")

    p_move = sub.add_parser("move")
    p_move.add_argument("--angle", type=float, required=True)

    p_servo = sub.add_parser("servo")
    p_servo.add_argument("--angle", type=float, required=True)

    sub.add_parser("lcd")
    sub.add_parser("keypad")

    p_blink = sub.add_parser("blink")
    p_blink.add_argument(
        "--bcm",
        type=int,
        default=24,
        help="GPIO BCM à faire clignoter (24 = pompe carte / pin physique 18)",
    )

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "status": cmd_status,
        "pins": cmd_pins,
        "home": cmd_home,
        "scan": cmd_scan,
        "servo-calibrate": cmd_servo_calibrate,
        "servo-sweep": cmd_servo_sweep,
        "card-pick": cmd_card_pick,
        "card-release": cmd_card_release,
        "relays": cmd_relays,
        "lift-down": cmd_lift_down,
        "lift-up": cmd_lift_up,
        "pick-cycle": cmd_pick_cycle,
        "step": lambda: cmd_step(args.steps, args.dir),
        "move": lambda: cmd_move(args.angle),
        "servo": lambda: cmd_servo(args.angle),
        "lcd": cmd_lcd,
        "keypad": cmd_keypad,
        "blink": lambda: cmd_blink(args.bcm),
    }
    commands[args.command]()


if __name__ == "__main__":
    main()
