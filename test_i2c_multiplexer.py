import unittest

from i2c_multiplexer import I2cMultiplexer


class FakeI2cBus:
    def __init__(self) -> None:
        self.writes: list[tuple[int, int]] = []

    def write_byte(self, device_address: int, value: int) -> None:
        self.writes.append((device_address, value))


class I2cMultiplexerTests(unittest.TestCase):
    def test_select_channel_writes_one_hot_mask(self) -> None:
        bus = FakeI2cBus()
        multiplexer = I2cMultiplexer(bus)

        multiplexer.select_channel(3)

        self.assertEqual(bus.writes, [(0x70, 0b00001000)])

    def test_invalid_channel_is_rejected(self) -> None:
        multiplexer = I2cMultiplexer(FakeI2cBus())

        with self.assertRaises(ValueError):
            multiplexer.select_channel(8)
