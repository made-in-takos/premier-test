"""
Relais pneumatiques — même logique que le sketch Arduino.

    digitalWrite(PompeVentousePin, HIGH);  # ON
    digitalWrite(PompeVentousePin, LOW);   # OFF
"""

import time

import config

RELAY_NAMES = (
    ("pump_card", "Pompe 1 carte"),
    ("valve_card", "EV 1 carte"),
    ("pump_lift", "Pompe 2 verin"),
    ("valve_lift", "EV 2 verin"),
)


def gpio_high_for(on):
    """Niveau GPIO (True = 3,3 V) pour allumer ou éteindre un relais."""
    return (not on) if config.RELAY_ACTIVE_LOW else bool(on)


class PneumaticController:
    def __init__(self):
        self._relays = {}
        self._pins = {
            "pump_card": config.GPIO_RELAY_PUMP_CARD,
            "valve_card": config.GPIO_RELAY_VALVE_CARD,
            "pump_lift": config.GPIO_RELAY_PUMP_LIFT,
            "valve_lift": config.GPIO_RELAY_VALVE_LIFT,
        }
        self._gpio = config.IS_RASPBERRY
        self._lift_level = 0

        if self._gpio:
            from gpiozero import DigitalOutputDevice

            for name, pin in self._pins.items():
                # active_high=True : on() = HIGH, comme digitalWrite(HIGH)
                self._relays[name] = DigitalOutputDevice(
                    pin, active_high=True, initial_value=gpio_high_for(False)
                )
            polarite = "LOW" if config.RELAY_ACTIVE_LOW else "HIGH"
            print(f"Relais : ON = GPIO {polarite} (comme Arduino HIGH si HIGH)")
        else:
            print("[SIMULATION] Relais")

        self.all_off()

    def _set(self, name, on):
        high = gpio_high_for(on)
        if self._gpio:
            if high:
                self._relays[name].on()
            else:
                self._relays[name].off()
        print(f"  {name} GPIO {self._pins[name]} → {'HIGH' if high else 'LOW'} ({'ON' if on else 'OFF'})")

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
        print("  Ventouse : libération…")
        self._card_off()
        time.sleep(config.VACUUM_OFF_DELAY_S)

    def down(self):
        print("  Vérin : descente…")
        self._set("pump_lift", config.LIFT_DOWN_PUMP_ON)
        self._set("valve_lift", config.LIFT_DOWN_VALVE_ON)
        time.sleep(config.LIFT_DOWN_HOLD_S)
        self._lift_off()
        self._lift_level += 1
        time.sleep(config.LIFT_SETTLE_S)

    def up(self):
        print("  Vérin : montée…")
        if config.LIFT_UP_HOLD_S > 0:
            self._set("pump_lift", config.LIFT_UP_PUMP_ON)
            self._set("valve_lift", config.LIFT_UP_VALVE_ON)
            time.sleep(config.LIFT_UP_HOLD_S)
        self._lift_off()
        self._lift_level = max(0, self._lift_level - 1)
        time.sleep(config.LIFT_SETTLE_S)

    def to_pickup_height(self):
        if self._lift_level == 0:
            self.down()

    def to_transport_height(self):
        while self._lift_level > 0:
            self.up()

    def to_deposit_height(self):
        self.to_pickup_height()

    def test_each(self, hold_s=None):
        """Comme le case '3' Arduino : chaque relais ON 2 s, OFF 2 s."""
        hold_s = config.HARDWARE_TEST_HOLD_S if hold_s is None else hold_s
        self.all_off()
        for name, label in RELAY_NAMES:
            print(f"--- {label} ON ---")
            self._set(name, True)
            time.sleep(hold_s)
            print(f"--- {label} OFF ---")
            self._set(name, False)
            time.sleep(hold_s)
        self.all_off()

    @property
    def lift_level(self):
        return self._lift_level

    def cleanup(self):
        self.all_off()
        for relay in self._relays.values():
            relay.close()
        self._relays = {}
