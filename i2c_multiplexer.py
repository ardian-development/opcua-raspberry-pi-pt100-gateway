"""Small, generic I2C multiplexer abstraction for a Raspberry Pi demo setup."""

from __future__ import annotations

from typing import Protocol


class ByteWritableI2cBus(Protocol):
    """Minimal interface implemented by common SMBus adapters."""

    def write_byte(self, device_address: int, value: int) -> None:
        """Write one byte to an I2C device."""


class I2cMultiplexer:
    """Select channels on a PCA9548A-compatible I2C multiplexer.

    The class deliberately models only the common one-hot channel selection
    command. It keeps hardware addressing out of the OPC UA server and makes
    the adapter easy to substitute in tests.
    """

    def __init__(self, bus: ByteWritableI2cBus, address: int = 0x70) -> None:
        self._bus = bus
        self._address = address

    def select_channel(self, channel: int) -> None:
        """Enable exactly one channel (0 through 7)."""
        if not 0 <= channel <= 7:
            raise ValueError("I2C multiplexer channel must be between 0 and 7")
        self._bus.write_byte(self._address, 1 << channel)

    def disable_all_channels(self) -> None:
        """Disconnect all downstream I2C channels."""
        self._bus.write_byte(self._address, 0x00)
