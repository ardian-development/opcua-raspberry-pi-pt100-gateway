"""Publish PT100 readings and sensor IDs through a small OPC UA gateway."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from asyncua import Server, ua

from pt100_backend import Pt100Backend, SensorConfig, SimulatedPt100Backend


LOG = logging.getLogger(__name__)
NAMESPACE_URI = "urn:ardian-development:opcua-pt100-gateway"


@dataclass
class OpcUaSensorNodes:
    sensor_id: ua.Node
    temperature_celsius: ua.Node
    last_update: ua.Node
    status: ua.Node


def load_sensor_config(path: Path) -> list[SensorConfig]:
    """Load only the small, non-secret hardware mapping used by the gateway."""
    raw_config = json.loads(path.read_text(encoding="utf-8"))
    return [SensorConfig(**item) for item in raw_config["sensors"]]


class Pt100OpcUaGateway:
    def __init__(self, backend: Pt100Backend, sensors: list[SensorConfig], endpoint: str) -> None:
        self._backend = backend
        self._sensors = sensors
        self._endpoint = endpoint
        self._server = Server()

    async def run(self) -> None:
        await self._server.init()
        self._server.set_endpoint(self._endpoint)
        self._server.set_server_name("PT100 OPC UA Gateway Demo")
        namespace_index = await self._server.register_namespace(NAMESPACE_URI)
        nodes = await self._create_address_space(namespace_index)

        LOG.info("Starting gateway at %s for %d sensor(s)", self._endpoint, len(self._sensors))
        async with self._server:
            while True:
                await self._publish_all(nodes)
                await asyncio.sleep(2)

    async def _create_address_space(self, namespace_index: int) -> dict[str, OpcUaSensorNodes]:
        sensors_folder = await self._server.nodes.objects.add_folder(namespace_index, "Pt100Sensors")
        nodes: dict[str, OpcUaSensorNodes] = {}

        for sensor in self._sensors:
            sensor_object = await sensors_folder.add_object(namespace_index, sensor.name)
            nodes[sensor.name] = OpcUaSensorNodes(
                sensor_id=await sensor_object.add_variable(namespace_index, "SensorId", "pending"),
                temperature_celsius=await sensor_object.add_variable(
                    namespace_index, "TemperatureCelsius", 0.0, ua.VariantType.Double
                ),
                last_update=await sensor_object.add_variable(
                    namespace_index,
                    "LastUpdate",
                    datetime.now(UTC),
                    ua.VariantType.DateTime,
                ),
                status=await sensor_object.add_variable(namespace_index, "Status", "initializing"),
            )
        return nodes

    async def _publish_all(self, nodes: dict[str, OpcUaSensorNodes]) -> None:
        for sensor in self._sensors:
            sensor_nodes = nodes[sensor.name]
            try:
                reading = await self._backend.read(sensor)
                await sensor_nodes.sensor_id.write_value(reading.sensor_id)
                await sensor_nodes.temperature_celsius.write_value(reading.temperature_celsius)
                await sensor_nodes.last_update.write_value(reading.measured_at)
                await sensor_nodes.status.write_value("ok")
                LOG.info("%s: %.2f C (%s)", sensor.name, reading.temperature_celsius, reading.sensor_id)
            except (OSError, ValueError) as error:
                LOG.warning("Could not read %s: %s", sensor.name, error)
                await sensor_nodes.status.write_value(f"read error: {error}")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PT100 to OPC UA gateway demo")
    parser.add_argument("--config", type=Path, default=Path("config.example.json"))
    parser.add_argument("--endpoint", default="opc.tcp://0.0.0.0:4840/pt100-gateway/")
    return parser.parse_args()


async def main() -> None:
    args = parse_arguments()
    sensors = load_sensor_config(args.config)
    gateway = Pt100OpcUaGateway(SimulatedPt100Backend(), sensors, args.endpoint)
    await gateway.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    asyncio.run(main())
