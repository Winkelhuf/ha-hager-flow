"""Basis-Sensor-Klasse für Hager flow."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from .descriptions import HagerFlowSensorEntityDescription
from ..entity.base import IntegrationBlueprintEntity

# Übersetzungstabelle für den SG Ready Status
SG_READY_MAPPING = {
    1: "Blockiert",
    2: "Normalbetrieb",
    3: "Anlaufempfehlung",
    4: "Anlaufbefehl"
}

# Übersetzungstabelle für den PowerMeter Typ
METER_TYPE_MAPPING = {
    0: "Undefiniert",
    1: "Hauptzähler (Root)",
    2: "Zusatzerzeugung",
    3: "Zusatzverbraucher",
    4: "Zusatzverbraucher Heizung/Klima",
    5: "Farm",
    6: "Ungenutzt",
    7: "Wallbox",
    8: "Farm Erweitert"
}

class IntegrationBlueprintSensor(IntegrationBlueprintEntity, SensorEntity):
    """Repräsentiert einen Hager Modbus Sensor."""

    entity_description: HagerFlowSensorEntityDescription

    def __init__(self, coordinator, description: HagerFlowSensorEntityDescription, entry_id: str) -> None:
        """Initialisiere den Sensor mit Hub-spezifischer ID."""
        super().__init__(coordinator, description, entry_id)
        
        # Optionen für ENUM-Sensoren zuweisen
        if hasattr(description, "options") and description.options:
            self._attr_options = description.options
        elif isinstance(description, dict) and "options" in description:
            self._attr_options = description["options"]

    @property
    def native_value(self) -> any:
        """Gibt den aktuellen Wert aus dem Coordinator zurück."""
        raw_value = self.coordinator.data.get(self.entity_description.key)
        
        if raw_value is None:
            return None

        # Filter / Übersetzung: SG Ready Status
        if "sg_ready_status" in self.entity_description.key:
            return SG_READY_MAPPING.get(int(raw_value), f"Unbekannt ({raw_value})")

        # Filter / Übersetzung: PowerMeter Typ
        if "meter_type" in self.entity_description.key:
            return METER_TYPE_MAPPING.get(int(raw_value), f"Unbekannt ({raw_value})")

        # Filter / Bit-Berechnung: Power Priorität - Bit 0 (Ladeziel)
        if self.entity_description.key == "power_prioritaet_ziel":
            bit_0 = int(raw_value) & 0x01
            return "Batterie zuerst" if bit_0 == 1 else "Auto zuerst"

        # Filter / Bit-Berechnung: Power Priorität - Bit 1 (Batterie-Entladung ins Auto)
        if self.entity_description.key == "power_prioritaet_entladung":
            bit_1 = (int(raw_value) >> 1) & 0x01
            return "Erlaubt" if bit_1 == 1 else "Verboten"

        return raw_value
