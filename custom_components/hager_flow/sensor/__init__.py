"""Sensor-Plattform für die Hager flow Integration."""
from typing import TYPE_CHECKING
from homeassistant.components.sensor import SensorStateClass

from .descriptions import (
    ENTITY_DESCRIPTIONS, 
    METER_SENSOR_TEMPLATES, 
    WALLBOX_SENSOR_TEMPLATES, 
    SG_READY_SENSOR_TEMPLATES,
    HagerFlowSensorEntityDescription
)
from .entity import IntegrationBlueprintSensor

PARALLEL_UPDATES = 0

async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Richte die Sensor-Plattform dynamisch ein."""
    coordinator = entry.runtime_data.coordinator
    entities = []

    # 1. Feste Hauptsensoren hinzufügen
    for description in ENTITY_DESCRIPTIONS:
        entities.append(IntegrationBlueprintSensor(coordinator, description, entry.entry_id))

    # 2. Dynamisch Sensoren für erkannte RTU-Zähler hinzufügen (30-37)
    if coordinator.discovered_meters:
        for slave, meter_name in coordinator.discovered_meters.items():
            for template in METER_SENSOR_TEMPLATES:
                dynamic_desc = HagerFlowSensorEntityDescription(
                    key=f"meter_{slave}_{template['key_suffix']}",
                    name=f"{meter_name} {template['name_suffix']}",
                    register_address=template["addr"],
                    slave_id=slave,
                    data_type=template["type"],
                    device_class=template.get("device_class"),
                    native_unit_of_measurement=template["unit"],
                    state_class=SensorStateClass.MEASUREMENT,
                )
                entities.append(IntegrationBlueprintSensor(coordinator, dynamic_desc, entry.entry_id))

    # 3. Dynamisch Sensoren für erkannte Wallboxen hinzufügen (1-7)
    if coordinator.discovered_wallboxes:
        for slave, wb_name in coordinator.discovered_wallboxes.items():
            for template in WALLBOX_SENSOR_TEMPLATES:
                s_class = None if template["type"] == "string" else SensorStateClass.MEASUREMENT
                
                dynamic_desc = HagerFlowSensorEntityDescription(
                    key=f"wb_{slave}_{template['key_suffix']}",
                    name=f"{wb_name} {template['name_suffix']}",
                    register_address=template["addr"],
                    slave_id=slave,
                    data_type=template["type"],
                    device_class=template.get("device_class"),
                    native_unit_of_measurement=template["unit"],
                    state_class=s_class,
                )
                entities.append(IntegrationBlueprintSensor(coordinator, dynamic_desc, entry.entry_id))

    # 4. Dynamisch Sensoren für erkannte SG Ready Einheiten hinzufügen (50-59)
    if coordinator.discovered_sg_ready:
        for slave, sg_name in coordinator.discovered_sg_ready.items():
            for template in SG_READY_SENSOR_TEMPLATES:
                s_class = None if template["type"] == "string" else SensorStateClass.MEASUREMENT
                
                dynamic_desc = HagerFlowSensorEntityDescription(
                    key=f"sg_{slave}_{template['key_suffix']}",
                    name=f"{sg_name} {template['name_suffix']}",
                    register_address=template["addr"],
                    slave_id=slave,
                    data_type=template["type"],
                    string_count=template.get("count", 1),
                    device_class=template.get("device_class"),
                    native_unit_of_measurement=template["unit"],
                    state_class=s_class,
                )
                entities.append(IntegrationBlueprintSensor(coordinator, dynamic_desc, entry.entry_id))

    async_add_entities(entities)
