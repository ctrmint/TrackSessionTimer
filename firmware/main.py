"""Memory-safe MicroPython entry point for Track Session Timer."""

from lcd_1inch28 import LCD_1inch28


def main():
    # The 115,200-byte framebuffer must be the first large allocation. Import
    # the application runtime only after this succeeds to avoid RP2040 heap
    # fragmentation as features are added.
    lcd = LCD_1inch28()
    from application import run_application

    return run_application(lcd)


if __name__ == "__main__":
    main()
