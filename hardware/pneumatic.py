"""
Pneumatique — 2 circuits independants :

  Circuit 1 (Pompe 1 + EV 1) : ventouse carte
    - pick()    → aspiration
    - release() → liberation

  Circuit 2 (Pompe 2 + EV 2) : verin vertical (etage)
    - down()    → descendre d'un etage
    - up()      → monter d'un etage
"""

import time

import config
from hardware.gpio_setup import configure_pin_factory


class PneumaticController:
    def __init__(self):
        configure_pin_factory()
        self._relays = {}
        self._gpio = config.IS_RASPBERRY
        self._lift_level = 0  # 0 = haut (transport), >0 = etages descendus

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
        if self._gpio:
            if state:
                self._relays[name].on()
            else:
                self._relays[name].off()
        else:
            print(f"  [SIM] {name} → {'ON' if state else 'OFF'}")

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
        """Aspire la carte (Pompe 1 + EV 1 ON)."""
        print("  Ventouse : aspiration…")
        self._set("valve_card", True)
        self._set("pump_card", True)
        time.sleep(config.VACUUM_ON_DELAY_S)

    def release(self):
        """Libere la carte (Pompe 1 + EV 1 OFF)."""
        print("  Ventouse : liberation…")
        self._card_off()
        time.sleep(config.VACUUM_OFF_DELAY_S)

    def down(self):
        """Descend le verin d'un etage (Pompe 2 + EV 2)."""
        print("  Verin : descente d'un etage…")
        self._set("pump_lift", config.LIFT_DOWN_PUMP_ON)
        self._set("valve_lift", config.LIFT_DOWN_VALVE_ON)
        time.sleep(config.LIFT_DOWN_HOLD_S)
        self._lift_off()
        self._lift_level += 1
        time.sleep(config.LIFT_SETTLE_S)
        print(f"  Verin : etage {self._lift_level}")

    def up(self):
        """Remonte le verin d'un etage."""
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
        """Position basse — niveau du tas de cartes."""
        if self._lift_level == 0:
            self.down()

    def to_transport_height(self):
        """Position haute — degagement pour rotation du bras."""
        while self._lift_level > 0:
            self.up()

    def to_deposit_height(self):
        """Position basse — depot de la carte."""
        self.to_pickup_height()

    @property
    def lift_level(self):
        return self._lift_level

    def cleanup(self):
        self.all_off()
        for relay in self._relays.values():
            relay.close()
