"""
Sorties GPIO — même méthode que le stepper qui fonctionne (gpiozero).

Les numéros du code sont BCM. Le header 40 broches utilise d'autres numéros.
"""

BCM_PHYSICAL = {
    2: 3,
    3: 5,
    4: 7,
    5: 29,
    6: 31,
    7: 26,
    8: 24,
    9: 21,
    10: 19,
    11: 23,
    12: 32,
    13: 33,
    14: 8,
    15: 10,
    16: 36,
    17: 11,
    18: 12,
    19: 35,
    20: 38,
    21: 40,
    22: 15,
    23: 16,
    24: 18,
    25: 22,
    26: 37,
    27: 13,
}


def physical(bcm):
    return BCM_PHYSICAL.get(int(bcm))


def describe(bcm):
    header = physical(bcm)
    extra = f"pin physique {header}" if header else "pin physique ?"
    return f"BCM {bcm} = {extra}"


def digital_output(bcm, initial_high=False):
    """Comme le ULN2003 : gpiozero, HIGH = 3,3 V, LOW = 0 V."""
    from gpiozero import DigitalOutputDevice

    return DigitalOutputDevice(bcm, active_high=True, initial_value=bool(initial_high))


def lgpio_chip_handle():
    """Même gpiochip que le stepper (gpiozero LGPIOFactory, chip 4 sur Pi 5)."""
    from gpiozero import Device
    from gpiozero.pins.lgpio import LGPIOFactory

    factory = Device.pin_factory
    if factory is None:
        Device.pin_factory = LGPIOFactory()
        factory = Device.pin_factory
    handle = getattr(factory, "_handle", None)
    if handle is None:
        raise RuntimeError(
            f"gpiozero factory {type(factory).__name__} n'expose pas lgpio "
            "(attendu sur Raspberry Pi 5)."
        )
    return handle


def claim_lgpio_output(bcm):
    """Réserve une broche en sortie lgpio, sans DigitalOutputDevice par-dessus."""
    import lgpio

    handle = lgpio_chip_handle()
    bcm = int(bcm)
    try:
        lgpio.gpio_free(handle, bcm)
    except Exception:
        pass
    lgpio.gpio_claim_output(handle, bcm)
    return lgpio, handle, bcm


def blink(bcm, times=5, on_s=0.5, off_s=0.5):
    """Bascule HIGH / LOW — même driver que le stepper qui marche."""
    import time

    print(f"Clignotement {describe(bcm)}  ({times}× HIGH 3,3 V / LOW 0 V)")
    pin = digital_output(bcm, initial_high=False)
    try:
        for i in range(int(times)):
            print(f"  HIGH 3,3 V  ({i + 1}/{times})")
            pin.on()
            time.sleep(on_s)
            print("  LOW 0 V")
            pin.off()
            time.sleep(off_s)
    finally:
        pin.off()
        pin.close()
