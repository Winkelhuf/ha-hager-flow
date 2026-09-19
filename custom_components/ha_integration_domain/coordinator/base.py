"""DataUpdateCoordinator für die Hager flow Integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from pymodbus.client import ModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class HagerFlowCoordinator(DataUpdateCoordinator):
    """Klasse zur Verwaltung des Datenabrufs über Modbus TCP."""

    def __init__(self, hass: HomeAssistant, host: str) -> None:
        """Initialisierung des Coordinators."""
        self.host = host
        # Port 502 aus deiner YAML
        self.client = ModbusTcpClient(host=self.host, port=502)
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            # Aktualisierungsintervall: 5 Sekunden
            update_interval=timedelta(seconds=5),
        )

    def _read_register_value(self, address: int, slave: int, data_type: str) -> int | float | None:
        """Hilfsfunktion zum Auslesen und Dekodieren eines Modbus-Registers."""
        try:
            count = 2 if data_type in ["int32", "uint32"] else 1
            result = self.client.read_holding_registers(address, count, slave=slave)
            
            if result.isError():
                _LOGGER.error("Fehler beim Lesen von Register %s (Slave %s)", address, slave)
                return None

            decoder = BinaryPayloadDecoder.fromRegisters(
                result.registers, 
                byteorder=Endian.BIG, 
                wordorder=Endian.BIG
            )
            
            if data_type == "int32":
                return decoder.decode_32bit_int()
            if data_type == "uint32":
                return decoder.decode_32bit_uint()
            if data_type == "uint16":
                return decoder.decode_16bit_uint()
                
            return result.registers
            
        except Exception as err:
            _LOGGER.error("Modbus-Fehler an Adresse %s: %s", address, err)
            return None

    async def _async_update_data(self) -> dict[str, any]:
        """Holt die neuesten Daten vom Hager-System."""
        if not self.client.connected:
            await self.hass.async_add_executor_job(self.client.connect)

        # Importiert die Sensor-Definitionen
        from ..sensor.descriptions import ENTITY_DESCRIPTIONS

        data = {}
        
        for description in ENTITY_DESCRIPTIONS:
            val = await self.hass.async_add_executor_job(
                self._read_register_value,
                description.register_address,
                description.slave_id,
                description.data_type
            )
            if val is not None:
                data[description.key] = val

        if not data:
            raise UpdateFailed("Keine Daten vom Hager System empfangen")

        return data
