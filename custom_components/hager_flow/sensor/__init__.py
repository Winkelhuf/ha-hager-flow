"""Sensor-Plattform für die Hager flow Integration."""
from typing import TYPE_CHECKING
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass

from .descriptions import (
    ENTITY_DESCRIPTIONS, 
    METER_SENSOR_TEMPLATES, 
    WALLBOX_SENSOR_TEMPLATES, 
    SG_READY_SENSOR_TEMPLATES,
    HagerFlowSensorEntityDescription
)
from .energy import (
    ENERGY_ENTITY_DESCRIPTIONS,
    METER_ENERGY_TEMPLATES,
    HagerFlowEnergySensor,
    build_meter_energy_description,
)
from .entity import HagerFlowSensor

PARALLEL_UPDATES = 0

async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Richte die Sensor-Plattform dynamisch ein."""
    coordinator = entry.runtime_data.coordinator
    entities = []

    # 1. Feste Hauptsensoren hinzufügen
    for description in ENTITY_DESCRIPTIONS:
        entities.append(HagerFlowSensor(coordinator, description, entry.entry_id))

    # 1b. Energiesensoren (kWh) hinzufügen, die aus den Leistungswerten oben
    #     integriert werden – optimiert für das Home Assistant Energie-Dashboard.
    for energy_description in ENERGY_ENTITY_DESCRIPTIONS:
        entities.append(HagerFlowEnergySensor(coordinator, energy_description, entry.entry_id))

    # 2. Dynamisch Sensoren für erkannte RTU-Zähler hinzufügen (30-37)
    if coordinator.discovered_meters:
        for slave, meter_name in coordinator.discovered_meters.items():
            for template in METER_SENSOR_TEMPLATES:
                dynamic_desc = HagerFlowSensorEntityDescription(
                    key=f"meter_{slave}_{template['key_suffix']}",
                    register_address=template["addr"],
                    slave_id=slave,
                    data_type=template["type"],
                    device_class=template.get("device_class"),
                    native_unit_of_measurement=template["unit"],
                    state_class=SensorStateClass.MEASUREMENT,
                    suggested_display_precision=template.get("precision"),
                )
                entities.append(HagerFlowSensor(coordinator, dynamic_desc, entry.entry_id))

            # 2b. Energiesensoren (kWh) für diesen Zähler ableiten – läuft für
            #     JEDEN per Auto-Discovery gefundenen Zähler automatisch mit,
            #     auch für erst später hinzukommende Geräte.
            for energy_template in METER_ENERGY_TEMPLATES:
                energy_desc = build_meter_energy_description(
                    slave, energy_template["key_suffix"], energy_template["direction"]
                )
                entities.append(HagerFlowEnergySensor(coordinator, energy_desc, entry.entry_id))

    # 3. Dynamisch Sensoren für erkannte Wallboxen hinzufügen (1-7)
    if coordinator.discovered_wallboxes:
        for slave, wb_name in coordinator.discovered_wallboxes.items():
            for template in WALLBOX_SENSOR_TEMPLATES:
                if template["type"] == "string":
                    s_class = None
                elif template.get("device_class") == SensorDeviceClass.ENERGY:
                    # Kumulative kWh-Zähler (Register zählen nur hoch) -> TOTAL_INCREASING,
                    # sonst wären diese Sensoren im Energie-Dashboard nicht auswählbar.
                    s_class = SensorStateClass.TOTAL_INCREASING
                else:
                    s_class = SensorStateClass.MEASUREMENT
                
                dynamic_desc = HagerFlowSensorEntityDescription(
                    key=f"wb_{slave}_{template['key_suffix']}",
                    register_address=template["addr"],
                    slave_id=slave,
                    data_type=template["type"],
                    device_class=template.get("device_class"),
                    native_unit_of_measurement=template["unit"],
                    state_class=s_class,
                    suggested_display_precision=template.get("precision"),
                )
                entities.append(HagerFlowSensor(coordinator, dynamic_desc, entry.entry_id))

    # 4. Dynamisch Sensoren für erkannte SG Ready Einheiten hinzufügen (50-59)
    if coordinator.discovered_sg_ready:
        for slave, sg_name in coordinator.discovered_sg_ready.items():
            for template in SG_READY_SENSOR_TEMPLATES:
                s_class = None if template["type"] == "string" else SensorStateClass.MEASUREMENT
                
                dynamic_desc = HagerFlowSensorEntityDescription(
                    key=f"sg_{slave}_{template['key_suffix']}",
                    register_address=template["addr"],
                    slave_id=slave,
                    data_type=template["type"],
                    string_count=template.get("count", 1),
                    device_class=template.get("device_class"),
                    native_unit_of_measurement=template["unit"],
                    state_class=s_class,
                )
                entities.append(HagerFlowSensor(coordinator, dynamic_desc, entry.entry_id))

    async_add_entities(entities)