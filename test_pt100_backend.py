import unittest

from pt100_backend import SensorConfig, SimulatedPt100Backend


class SimulatedPt100BackendTests(unittest.IsolatedAsyncioTestCase):
    async def test_read_returns_a_sensor_id_and_temperature(self) -> None:
        sensor = SensorConfig("Pt100Channel0", 0, 72, 16, 32)

        reading = await SimulatedPt100Backend().read(sensor)

        self.assertEqual(reading.sensor_id, "PT100-DEMO-CH00")
        self.assertGreater(reading.temperature_celsius, -20.0)
        self.assertLess(reading.temperature_celsius, 90.0)
