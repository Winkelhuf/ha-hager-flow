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

# 2. DYNAMISCHE METER-VORLAGEN (Slaves 30-37)
METER_SENSOR_TEMPLATES: tuple[dict[str, any], ...] = (
    {"key_suffix": "leistung", "name_suffix": "Leistung", "addr": 4153, "type": "int32", "scale": 1.0, "unit": UnitOfPower.WATT},
    {"key_suffix": "leistung_l1", "name_suffix": "Leistung L1", "addr": 4155, "type": "int32", "scale": 1.0, "unit": UnitOfPower.WATT},
    {"key_suffix": "leistung_l2", "name_suffix": "Leistung L2", "addr": 4157, "type": "int32", "scale": 1.0, "unit": UnitOfPower.WATT},
    {"key_suffix": "leistung_l3", "name_suffix": "Leistung L3", "addr": 4159, "type": "int32", "scale": 1.0, "unit": UnitOfPower.WATT},
    {"key_suffix": "energie_wh", "name_suffix": "Energie Wh", "addr": 4164, "type": "uint32", "scale": 1.0, "unit": "Wh"},
)

# 3. DYNAMISCHE WALLBOX-VORLAGEN (Slaves 1-7)
WALLBOX_SENSOR_TEMPLATES: tuple[dict[str, any], ...] = (
    {"key_suffix": "firmware", "name_suffix": "Firmware", "addr": 4165, "type": "string", "count": 32, "scale": 1.0, "unit": None},
    {"key_suffix": "ip_adresse", "name_suffix": "IP Adresse", "addr": 5385, "type": "string", "count": 8, "scale": 1.0, "unit": None},
    {"key_suffix": "solar_leistung", "name_suffix": "Witty Solar Leistung", "addr": 5125, "type": "int16", "scale": 1.0, "unit": UnitOfPower.WATT},
    {"key_suffix": "gesamtenergie_geladen", "name_suffix": "Gesamtenergie geladen", "addr": 4609, "type": "uint32", "scale": 0.001, "unit": "kWh"},
    {"key_suffix": "solarenergie_geladen", "name_suffix": "Solarenergie geladen", "addr": 4611, "type": "uint32", "scale": 0.001, "unit": "kWh"},
    {"key_suffix": "verbunden", "name_suffix": "Verbunden", "addr": 4613, "type": "uint16", "scale": 1.0, "unit": None},
    {"key_suffix": "boostmodus", "name_suffix": "Boostmodus", "addr": 4631, "type": "uint16", "scale": 1.0, "unit": None},
    {"key_suffix": "ladesession_badge", "name_suffix": "Ladesession Badge", "addr": 4929, "type": "string", "count": 16, "scale": 1.0, "unit": None},
    {"key_suffix": "ladung_gesamt_session", "name_suffix": "Ladung Gesamt aktuelle Session", "addr": 4950, "type": "uint32", "scale": 0.001, "unit": "kWh"},
    {"key_suffix": "ladung_netz_session", "name_suffix": "Ladung Netz aktuelle Session", "addr": 4952, "type": "uint32", "scale": 0.001, "unit": "kWh"},
    {"key_suffix": "ladung_pv_session", "name_suffix": "Ladung PV aktuelle Session", "addr": 4954, "type": "uint32", "scale": 0.001, "unit": "kWh"},
    {"key_suffix": "ladesession_rfid", "name_suffix": "Ladesession RFID Karte", "addr": 5412, "type": "string", "count": 16, "scale": 1.0, "unit": None},
)
