"""Sensor descriptions for the Hager flow integration."""
from __future__ import annotations

from dataclasses import dataclass
from homeassistant.components.sensor import SensorEntityDescription, SensorStateClass, SensorDeviceClass
from homeassistant.const import UnitOfPower, PERCENTAGE

@dataclass(frozen=True, kw_only=True)
class HagerFlowSensorEntityDescription(SensorEntityDescription):
    """Description for a Hager Flow Modbus register."""
    register_address: int
    slave_id: int
    data_type: str
    scale: float = 1.0
    string_count: int = 1  # Default 1 register (2 bytes) for numeric values

# 1. MAIN SENSORS (Always present - Slave 0)
ENTITY_DESCRIPTIONS: tuple[HagerFlowSensorEntityDescription, ...] = (
    HagerFlowSensorEntityDescription(
        key="emc_seriennummer",
        register_address=48,
        slave_id=0,
        data_type="string",
        string_count=16,
    ),
    HagerFlowSensorEntityDescription(
        key="emc_firmware",
        register_address=64,
        slave_id=0,
        data_type="string",
        string_count=16,
    ),
    HagerFlowSensorEntityDescription(
        key="power_prioritaet_ziel",
        register_address=513,
        slave_id=0,
        data_type="uint16",
        device_class=SensorDeviceClass.ENUM,
    ),
    HagerFlowSensorEntityDescription(
        key="power_prioritaet_entladung",
        register_address=513,
        slave_id=0,
        data_type="uint16",
        device_class=SensorDeviceClass.ENUM,
    ),
    HagerFlowSensorEntityDescription(
        key="battery_power",
        register_address=4138,
        slave_id=0,
        data_type="int32",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    HagerFlowSensorEntityDescription(
        key="emc_autarkie_letzte_stunde",
        register_address=4224,
        slave_id=0,
        data_type="uint16",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    HagerFlowSensorEntityDescription(
        key="emc_eigenverbrauch_letzte_stunde",
        register_address=4225,
        slave_id=0,
        data_type="uint16",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    HagerFlowSensorEntityDescription(
        key="pv_leistung_gesamt",
        register_address=4126,
        slave_id=0,
        data_type="uint32",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    HagerFlowSensorEntityDescription(
        key="batterie_soc",
        register_address=4146,
        slave_id=0,
        data_type="uint16",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    HagerFlowSensorEntityDescription(
        key="hausverbrauch_gesamt",
        register_address=4151,
        slave_id=0,
        data_type="int32",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    HagerFlowSensorEntityDescription(
        key="hausanschluss_leistung",
        register_address=4102,
        slave_id=0,
        data_type="int32",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
)

# 2. DYNAMIC METER TEMPLATES (Slaves 30-37)
METER_SENSOR_TEMPLATES: tuple[dict[str, any], ...] = (
    {"key_suffix": "leistung", "addr": 4153, "type": "int32", "scale": 1.0, "unit": UnitOfPower.WATT, "device_class": SensorDeviceClass.POWER, "precision": 0},
    {"key_suffix": "leistung_l1", "addr": 4155, "type": "int32", "scale": 1.0, "unit": UnitOfPower.WATT, "device_class": SensorDeviceClass.POWER, "precision": 0},
    {"key_suffix": "leistung_l2", "addr": 4157, "type": "int32", "scale": 1.0, "unit": UnitOfPower.WATT, "device_class": SensorDeviceClass.POWER, "precision": 0},
    {"key_suffix": "leistung_l3", "addr": 4159, "type": "int32", "scale": 1.0, "unit": UnitOfPower.WATT, "device_class": SensorDeviceClass.POWER, "precision": 0},
    {
        "key_suffix": "meter_type", 
        "addr": 4148, 
        "type": "uint16", 
        "scale": 1.0, 
        "unit": None, 
        "device_class": SensorDeviceClass.ENUM,
    },
)

# 3. DYNAMISCHE WALLBOX-VORLAGEN (Slaves 1-7)
WALLBOX_SENSOR_TEMPLATES: tuple[dict[str, any], ...] = (
    {"key_suffix": "firmware", "addr": 4165, "type": "string", "count": 32, "scale": 1.0, "unit": None, "device_class": None},
    {"key_suffix": "ip_adresse", "addr": 5385, "type": "string", "count": 8, "scale": 1.0, "unit": None, "device_class": None},
    {"key_suffix": "solar_leistung", "addr": 5125, "type": "int16", "scale": 1.0, "unit": UnitOfPower.WATT, "device_class": SensorDeviceClass.POWER, "precision": 0},
    {"key_suffix": "gesamtenergie_geladen", "addr": 4609, "type": "uint32", "scale": 0.001, "unit": "kWh", "device_class": SensorDeviceClass.ENERGY},
    {"key_suffix": "solarenergie_geladen", "addr": 4611, "type": "uint32", "scale": 0.001, "unit": "kWh", "device_class": SensorDeviceClass.ENERGY},
    {"key_suffix": "verbunden", "addr": 4613, "type": "uint16", "scale": 1.0, "unit": None, "device_class": SensorDeviceClass.ENUM},
    {"key_suffix": "ladesession_badge", "addr": 4929, "type": "string", "count": 16, "scale": 1.0, "unit": None, "device_class": None},
    {"key_suffix": "ladung_gesamt_session", "addr": 4950, "type": "uint32", "scale": 0.001, "unit": "kWh", "device_class": SensorDeviceClass.ENERGY},
    {"key_suffix": "ladung_netz_session", "addr": 4952, "type": "uint32", "scale": 0.001, "unit": "kWh", "device_class": SensorDeviceClass.ENERGY},
    {"key_suffix": "ladung_pv_session", "addr": 4954, "type": "uint32", "scale": 0.001, "unit": "kWh", "device_class": SensorDeviceClass.ENERGY},
    {"key_suffix": "ladesession_rfid", "addr": 5412, "type": "string", "count": 16, "scale": 1.0, "unit": None, "device_class": None},
)

# 4. DYNAMISCHE SG-READY-VORLAGEN (Slaves 50-59)
SG_READY_SENSOR_TEMPLATES: tuple[dict[str, any], ...] = (
    {
        "key_suffix": "sg_ready_status", 
        "addr": 4152, 
        "type": "int32", 
        "scale": 1.0, 
        "unit": None, 
        "device_class": SensorDeviceClass.ENUM,
    },
)
