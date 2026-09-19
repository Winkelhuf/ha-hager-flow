"""Sensor-Beschreibungen für die Hager flow Integration."""
from __future__ import annotations

from dataclasses import dataclass
from homeassistant.components.sensor import SensorEntityDescription, SensorStateClass
from homeassistant.const import UnitOfPower, PERCENTAGE

@dataclass(frozen=True, kw_only=True)
class HagerFlowSensorEntityDescription(SensorEntityDescription):
    """Beschreibung für ein Hager Flow Modbus Register."""
    register_address: int
    slave_id: int
    data_type: str
    scale: float = 1.0

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
)
