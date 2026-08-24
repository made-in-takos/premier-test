"""
Pneumatique — 4 relais (2 pompes + 2 electrovannes).

Arduino : HIGH = pompe ON. Electrovanne piston inversee (valve_lift).
"""

from __future__ import annotations

import time

import config
from gpio_setup import configure_pin_factory
from relay_math import requested_on


class PneumaticController:
    def __init__(self):
        configure_pin_factory()
        self._relays = {}
        self._gpio = config.IS_RASPBERRY
        self._lift_level = 0

        if self._gpio:
            from gpiozero import DigitalOutputDevice

            active_high = not config.RELAY_ACTIVE_LOW
            pins = {
                "pump_card": config.GPIO_RELAY_PUMP_CARD,
                "valve_card": config.GPIO_RELAY_VALVE_CARD,
                "pump_lift": config.GPIO_RELAY_PUMP_LIFT,
                "valve_lift": config.GPIO_RELAY_VALVE_LIFT,
            }
            for name, pin in pins.items():
                self._relays[name] = DigitalOutputDevice(
                    pin, active_high=active_high, initial_value=False
                )
        else:
            print("[SIMULATION] Pneumatique — 2 circuits (carte + verin)")

    def _set(self, name, state):
        electric_on = requested_on(name, state, config.RELAY_INVERT_CHANNELS)
        if self._gpio:
            if electric_on:
                self._relays[name].on()
            else:
                self._relays[name].off()
        else:
            print(f"  [SIM] {name} logique={'ON' if state else 'OFF'} gpio={'ON' if electric_on else 'OFF'}")

    def _card_off(self):
        self._set("pump_card", False)
        self._set("valve_card", False)

    def _lift_off(self):
        self._set("pump_lift", False)
        self._set("valve_lift", False)

    def all_off(self):
        self._card_off()
        self._lift_off()

    def pick(self):
        print("  Ventouse : aspiration…")
        self._set("valve_card", True)
        self._set("pump_card", True)
        time.sleep(config.VACUUM_ON_DELAY_S)

    def release(self):
        print("  Ventouse : liberation…")
        self._card_off()
        time.sleep(config.VACUUM_OFF_DELAY_S)

    def down(self):
        print("  Verin : descente d'un etage…")
        self._set("pump_lift", config.LIFT_DOWN_PUMP_ON)
        self._set("valve_lift", config.LIFT_DOWN_VALVE_ON)
        time.sleep(config.LIFT_DOWN_HOLD_S)
        self._lift_off()
        self._lift_level += 1
        time.sleep(config.LIFT_SETTLE_S)
        print(f"  Verin : etage {self._lift_level}")

    def up(self):
        print("  Verin : montee d'un etage…")
        if config.LIFT_UP_HOLD_S > 0:
            self._set("pump_lift", config.LIFT_UP_PUMP_ON)
            self._set("valve_lift", config.LIFT_UP_VALVE_ON)
            time.sleep(config.LIFT_UP_HOLD_S)
        self._lift_off()
        self._lift_level = max(0, self._lift_level - 1)
        time.sleep(config.LIFT_SETTLE_S)
        print(f"  Verin : etage {self._lift_level}")

    def to_pickup_height(self):
        if self._lift_level == 0:
            self.down()

    def to_transport_height(self):
        while self._lift_level > 0:
            self.up()

    def to_deposit_height(self):
        self.to_pickup_height()

    @property
    def lift_level(self):
        return self._lift_level

    def cleanup(self):
        self.all_off()
        for relay in self._relays.values():
            relay.close()
