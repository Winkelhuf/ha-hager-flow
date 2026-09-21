"""Basis-Sensor-Klasse für Hager flow."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from .descriptions import HagerFlowSensorEntityDescription
from ..entity.base import IntegrationBlueprintEntity

# ENUM-Zustände sind sprachfreie Schlüssel (Register-Wert -> Schlüssel), gruppiert
# nach translation_key des Sensors. Die Anzeigetexte stehen in
# translations/<sprache>.json unter entity.sensor.<translation_key>.state.<schlüssel>
# und werden vom Frontend in der Sprache des angemeldeten Benutzers angezeigt.
STATE_MAPS: dict[str, dict[int, str]] = {
    "power_prioritaet_ziel": {0: "car_first", 1: "battery_first"},
    "power_prioritaet_entladung": {0: "forbidden", 1: "allowed"},
    "sg_ready_status": {1: "blocked", 2: "normal", 3: "start_recommendation", 4: "start_command"},
    "verbunden": {0: "no", 1: "yes"},
    "meter_type": {
        0: "undefined",
        1: "root",
        2: "additional_generation",
        3: "additional_consumer",
        4: "additional_consumer_heating_cooling",
        5: "farm",
        6: "unused",
        7: "wallbox",
        8: "farm_extended",
    },
}

# Sensoren, deren Wert ein einzelnes Bit eines Registers ist (Bit-Nummer).
# power_prioritaet_* teilen sich Register 513.
BIT_OF_STATE_SENSOR: dict[str, int] = {
    "power_prioritaet_ziel": 0,
    "power_prioritaet_entladung": 1,
}


class IntegrationBlueprintSensor(IntegrationBlueprintEntity, SensorEntity):
    """Repräsentiert einen Hager Modbus Sensor."""

    entity_description: HagerFlowSensorEntityDescription

    def __init__(self, coordinator, description: HagerFlowSensorEntityDescription, entry_id: str) -> None:
        """Initialisiere den Sensor."""
        super().__init__(coordinator, description, entry_id)

        # Zuordnung über den translation_key (nicht über Teilstrings im Key)
        self._states = STATE_MAPS.get(self._attr_translation_key)
        if self._states is not None and description.device_class == SensorDeviceClass.ENUM:
            self._attr_options = list(self._states.values())
            # ENUM-Sensoren liefern Text, keine Zahl: ohne state_class behandelt das
            # Frontend den Zustand als Text und übersetzt ihn (entity.sensor.<key>.state.*).
            self._attr_state_class = None

    @property
    def native_value(self) -> any:
        """Gibt den aktuellen Wert aus dem Coordinator zurück."""
        raw_value = self.coordinator.data.get(self.entity_description.key)

        if raw_value is None:
            return None

        if self._states is None:
            return raw_value

        value = int(raw_value)
        bit = BIT_OF_STATE_SENSOR.get(self._attr_translation_key)
        if bit is not None:
            value = (value >> bit) & 0x01

        # Unbekannte Register-Werte -> None ("unbekannt"): ein ENUM-Sensor darf
        # nur Werte aus seiner Optionsliste melden.
        return self._states.get(value)