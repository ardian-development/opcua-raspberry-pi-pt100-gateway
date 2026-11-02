"""Backends for reading a PT100-style temperature value through an I2C multiplexer."""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from i2c_multiplexer import I2cMultiplexer


@dataclass(frozen=True)
class SensorConfig:
    name: str
    multiplexer_channel: int
    i2c_address: int
    temperature_register: int
    sensor_id_register: int
    sensor_id_length: int = 16


@dataclass(frozen=True)
class Pt100Reading:
    sensor_id: str
    temperature_celsius: float
    measured_at: datetime


class Pt100Backend(Protocol):
    async def read(self, sensor: SensorConfig) -> Pt100Reading:
        """Read one sensor and return a normalized engineering value."""


class I2cBlockReadBus(Protocol):
    def read_i2c_block_data(self, device_address: int, register: int, length: int) -> list[int]:
        """Read a register range from an I2C device."""


class I2cPt100BridgeBackend:
    """Adapter for a simple I2C-connected PT100 bridge.

    The bridge protocol is intentionally small and configurable for a portfolio
    example: it returns a signed, big-endian temperature in centi-degrees and
    an ASCII sensor ID. A real board can use the same interface with register
    values taken from its public data sheet.
    """

    def __init__(self, bus: I2cBlockReadBus, multiplexer: I2cMultiplexer) -> None:
        self._bus = bus
        self._multiplexer = multiplexer

    async def read(self, sensor: SensorConfig) -> Pt100Reading:
        return await asyncio.to_thread(self._read_sync, sensor)

    def _read_sync(self, sensor: SensorConfig) -> Pt100Reading:
        self._multiplexer.select_channel(sensor.multiplexer_channel)
        raw_temperature = self._bus.read_i2c_block_data(
            sensor.i2c_address, sensor.temperature_register, 2
        )
        raw_sensor_id = self._bus.read_i2c_block_data(
            sensor.i2c_address, sensor.sensor_id_register, sensor.sensor_id_length
        )

        temperature = int.from_bytes(bytes(raw_temperature), byteorder="big", signed=True) / 100
        sensor_id = bytes(raw_sensor_id).decode("ascii", errors="replace").rstrip("\x00").strip()
        if not sensor_id:
            raise ValueError(f"Sensor {sensor.name} returned an empty sensor ID")

        return Pt100Reading(sensor_id, temperature, datetime.now(UTC))


class SimulatedPt100Backend:
    """Runnable fallback that mirrors the public interface without hardware."""

    def __init__(self) -> None:
        self._values: dict[str, float] = {}

    async def read(self, sensor: SensorConfig) -> Pt100Reading:
        previous = self._values.get(sensor.name, 23.5)
        next_value = min(90.0, max(-20.0, previous + random.uniform(-0.2, 0.25)))
        self._values[sensor.name] = next_value
        return Pt100Reading(
            sensor_id=f"PT100-DEMO-CH{sensor.multiplexer_channel:02d}",
            temperature_celsius=round(next_value, 2),
            measured_at=datetime.now(UTC),
        )
