"""Basis-Sensor-Klasse für Hager flow."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from .descriptions import HagerFlowSensorEntityDescription
from ..entity.base import IntegrationBlueprintEntity

class IntegrationBlueprintSensor(IntegrationBlueprintEntity, SensorEntity):
    """Repräsentiert einen Hager Modbus Sensor."""

    entity_description: HagerFlowSensorEntityDescription

    def __init__(self, coordinator, description: HagerFlowSensorEntityDescription, entry_id: str) -> None:
        """Initialisiere den Sensor mit Hub-spezifischer ID."""
        # Ruft die Initialisierung der Basisklasse (base.py) auf, damit DeviceInfo & UniqueID gesetzt werden
        super().__init__(coordinator, description, entry_id)

    @property
    def native_value(self) -> any:
        """Gibt den aktuellen Wert aus dem Coordinator zurück."""
        return self.coordinator.data.get(self.entity_description.key)
