"""Sensor-Plattform für die Hager flow Integration."""
from typing import TYPE_CHECKING
from homeassistant.components.sensor import SensorStateClass

from .descriptions import ENTITY_DESCRIPTIONS, METER_SENSOR_TEMPLATES, HagerFlowSensorEntityDescription
from .entity import IntegrationBlueprintSensor

PARALLEL_UPDATES = 0

async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Richte die Sensor-Plattform dynamisch ein."""
    coordinator = entry.runtime_data.coordinator
    entities = []

    # 1. ALLE festen Hauptsensoren hinzufügen (wird jetzt garantiert für alle 5 gemacht!)
    for description in ENTITY_DESCRIPTIONS:
        entities.append(
            IntegrationBlueprintSensor(coordinator, description, entry.entry_id)
        )

    # 2. Dynamisch Sensoren für erkannte RTU-Zähler hinzufügen (falls welche antworten)
    if coordinator.discovered_meters:
        for slave, meter_name in coordinator.discovered_meters.items():
            for template in METER_SENSOR_TEMPLATES:
                dynamic_desc = HagerFlowSensorEntityDescription(
                    key=f"meter_{slave}_{template['key_suffix']}",
                    name=f"{meter_name} {template['name_suffix']}",
                    register_address=template["addr"],
                    slave_id=slave,
                    data_type=template["type"],
                    native_unit_of_measurement=template["unit"],
                    state_class=SensorStateClass.MEASUREMENT,
                )
                entities.append(
                    IntegrationBlueprintSensor(coordinator, dynamic_desc, entry.entry_id)
                )

    async_add_entities(entities)
