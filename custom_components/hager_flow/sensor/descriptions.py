"""Sensor-Beschreibungen für die Hager flow Integration."""
from __future__ import annotations

from dataclasses import dataclass
from homeassistant.components.sensor import SensorEntityDescription, SensorStateClass
from homeassistant.const import UnitOfPower, UnitOfElectricCurrent, PERCENTAGE

@dataclass(frozen=True, kw_only=True)
class HagerFlowSensorEntityDescription(SensorEntityDescription):
    """Beschreibung für ein Hager Flow Modbus Register."""
    register_address: int
    slave_id: int
    data_type: str
    scale: float = 1.0

# 1. HAUPTSENSOREN (Immer vorhanden - Slave 0 & 1)
ENTITY_DESCRIPTIONS: tuple[HagerFlowSensorEntityDescription, ...] = (
    HagerFlowSensorEntityDescription(
        key="pv_leistung_gesamt",
        name="EMC PV Leistung Gesamt",
        register_address=4126,
        slave_id=0,
        data_type="uint32",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    HagerFlowSensorEntityDescription(
        key="batterie_soc",
        name="EMC Batterie SOC",
        register_address=4146,
        slave_id=0,
        data_type="uint16",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    HagerFlowSensorEntityDescription(
        key="hausverbrauch_gesamt",
        name="EMC Hausverbrauch Gesamt",
        register_address=4151,
        slave_id=0,
        data_type="int32",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    HagerFlowSensorEntityDescription(
        key="main_leistung_gesamt",
        name="EMC Main Leistung Gesamt",
        register_address=4102,
        slave_id=0,
        data_type="int32",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    HagerFlowSensorEntityDescription(
        key="main_strom_l1",
        name="EMC Main Strom L1",
        register_address=4099,
        slave_id=1,
        data_type="uint16",
        scale=0.0001,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)

# 2. DYNAMISCHE METER-VORLAGEN (Werden für jeden erkannten Slave 30-37 erzeugt)
METER_SENSOR_TEMPLATES: tuple[dict[str, any], ...] = (
    {"key_suffix": "leistung", "name_suffix": "Leistung", "addr": 4153, "type": "int32", "unit": UnitOfPower.WATT},
    {"key_suffix": "leistung_l1", "name_suffix": "Leistung L1", "addr": 4155, "type": "int32", "unit": UnitOfPower.WATT},
    {"key_suffix": "leistung_l2", "name_suffix": "Leistung L2", "addr": 4157, "type": "int32", "unit": UnitOfPower.WATT},
    {"key_suffix": "leistung_l3", "name_suffix": "Leistung L3", "addr": 4159, "type": "int32", "unit": UnitOfPower.WATT},
    {"key_suffix": "energie_wh", "name_suffix": "Energie Wh", "addr": 4164, "type": "uint32", "unit": "Wh"},
)
