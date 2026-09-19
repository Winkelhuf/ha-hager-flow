"""DataUpdateCoordinator für die Hager flow Integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from pymodbus.client import ModbusTcpClient

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class HagerFlowCoordinator(DataUpdateCoordinator):
    """Klasse zur Verwaltung des Datenabrufs über Modbus TCP mit Auto-Discovery."""

    def __init__(self, hass: HomeAssistant, host: str) -> None:
        """Initialisierung des Coordinators."""
        self.host = host
        self.client = ModbusTcpClient(host=self.host, port=502)
        self.discovered_meters: dict[int, str] = {}
        self.discovered_wallboxes: dict[int, str] = {} # Speichert {slave_id: "Wallbox Name"}
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=5),
        )

    def _read_string_register(self, address: int, count: int, slave: int) -> str | None:
        """Liest ein Register aus und konvertiert es in lesbaren Text (String)."""
        try:
            result = self.client.read_holding_registers(address, count=count, device_id=slave)
            if result is None or result.isError():
                return None
            bytes_data = bytearray()
            for reg in result.registers:
                bytes_data.append((reg >> 8) & 0xFF)
                bytes_data.append(reg & 0xFF)
            return bytes_data.decode("utf-8", errors="ignore").strip("\x00").strip()
        except Exception:
            return None

    def discover_devices(self) -> None:
        """Scannt Meter (30-37) streng über Namen und Wallboxen (1-7) streng über Register 4613 (Verbunden == 1) ab."""
        if not self.client.connected:
            self.client.connect()
        
        # 1. Zähler scannen (Slaves 30-37) - Filter auf Name "EC"
        _LOGGER.info("Starte Auto-Discovery für Powermeter (Slaves 30-37)...")
        for slave in range(30, 38):
            name = self._read_string_register(4098, 15, slave)
            if name and name.upper().startswith("EC"):
                self.discovered_meters[slave] = name
                _LOGGER.info("Hager Powermeter auf Slave %s erkannt: '%s'", slave, name)

        # 2. Wallboxen scannen (Slaves 1-7) - Filter auf Register 4613 (Verbunden) == 1
        _LOGGER.info("Starte Auto-Discovery für Wallboxen (Slaves 1-7) über Register 4613...")
        for slave in range(1, 8):
            connected_check = self.client.read_holding_registers(4613, count=1, device_id=slave)
            
            if connected_check is not None and not connected_check.isError() and connected_check.registers[0] == 1:
                # Name auslesen versuchen, ansonsten sprechenden Fallback-Namen nutzen
                name = self._read_string_register(4099, 15, slave)
                if not name or len(name) == 0:
                    name = f"Witty Wallbox {slave}"
                
                self.discovered_wallboxes[slave] = name
                _LOGGER.info("Hager Wallbox auf Slave %s erfolgreich erkannt: '%s'", slave, name)

    def _read_register_value(self, address: int, slave: int, data_type: str, count: int = 1) -> any:
        """Hilfsfunktion zum Auslesen eines Modbus-Registers (Zahlen und Strings)."""
        try:
            if data_type == "string":
                return self._read_string_register(address, count, slave)

            read_count = 2 if data_type in ["int32", "uint32"] else 1
            result = self.client.read_holding_registers(address, count=read_count, device_id=slave)
            
            if result is None or result.isError():
                return None

            if data_type == "int32":
                return self.client.convert_from_registers(result.registers, self.client.DATATYPE.INT32)
            if data_type == "uint32":
                return self.client.convert_from_registers(result.registers, self.client.DATATYPE.UINT32)
            if data_type == "uint16":
                return self.client.convert_from_registers(result.registers, self.client.DATATYPE.UINT16)
            if data_type == "int16":
                return self.client.convert_from_registers(result.registers, self.client.DATATYPE.INT16)
                
            return result.registers
        except Exception:
            return None

    async def _async_update_data(self) -> dict[str, any]:
        """Holt die neuesten Daten vom Hager-System."""
        if not self.client.connected:
            await self.hass.async_add_executor_job(self.client.connect)

        if not self.discovered_meters and not self.discovered_wallboxes:
            await self.hass.async_add_executor_job(self.discover_devices)

        from ..sensor.descriptions import ENTITY_DESCRIPTIONS, METER_SENSOR_TEMPLATES, WALLBOX_SENSOR_TEMPLATES

        data = {}
        
        # 1. Statische Hauptsensoren lesen
        for description in ENTITY_DESCRIPTIONS:
            val = await self.hass.async_add_executor_job(
                self._read_register_value, description.register_address, description.slave_id, description.data_type
            )
            if val is not None:
                data[description.key] = val * description.scale

        # 2. Zusatz-Zähler abfragen (30-37)
        for slave, meter_name in self.discovered_meters.items():
            for template in METER_SENSOR_TEMPLATES:
                key = f"meter_{slave}_{template['key_suffix']}"
                val = await self.hass.async_add_executor_job(
                    self._read_register_value, template["addr"], slave, template["type"]
                )
                if val is not None:
                    data[key] = val * template["scale"]

        # 3. Wallboxen abfragen (1-7)
        for slave, wb_name in self.discovered_wallboxes.items():
            for template in WALLBOX_SENSOR_TEMPLATES:
                key = f"wb_{slave}_{template['key_suffix']}"
                cnt = template.get("count", 1)
                val = await self.hass.async_add_executor_job(
                    self._read_register_value, template["addr"], slave, template["type"], cnt
                )
                if val is not None:
                    data[key] = val if template["type"] == "string" else val * template["scale"]

        return data
