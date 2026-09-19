"""Basis-Sensor-Klasse für Hager flow."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .descriptions import HagerFlowSensorEntityDescription

class IntegrationBlueprintSensor(CoordinatorEntity, SensorEntity):
    """Repräsentiert einen Hager Modbus Sensor."""

    entity_description: HagerFlowSensorEntityDescription

    def __init__(self, coordinator, description: HagerFlowSensorEntityDescription, entry_id: str) -> None:
        """Initialisiere den Sensor mit Hub-spezifischer ID."""
        super().__init__(coordinator)
        self.entity_description = description
        # Durch entry_id wird der Sensor für jeden Hub absolut einzigartig!
        self._attr_unique_id = f"{entry_id}_{description.key}"


    @property
    def native_value(self) -> any:
        """Gibt den aktuellen Wert aus dem Coordinator zurück."""
        return self.coordinator.data.get(self.entity_description.key)
