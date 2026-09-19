"""Basis-Sensor-Klasse für Hager flow."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .descriptions import HagerFlowSensorEntityDescription

class IntegrationBlueprintSensor(CoordinatorEntity, SensorEntity):
    """Repräsentiert einen Hager Modbus Sensor."""

    entity_description: HagerFlowSensorEntityDescription

    def __init__(self, coordinator, description: HagerFlowSensorEntityDescription) -> None:
        """Initialisiere den Sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"hager_flow_{description.key}"

    @property
    def native_value(self) -> any:
        """Gibt den aktuellen Wert aus dem Coordinator zurück."""
        return self.coordinator.data.get(self.entity_description.key)
