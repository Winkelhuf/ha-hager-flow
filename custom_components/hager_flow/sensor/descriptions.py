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
        has_entity_name=True,
    ),
    HagerFlowSensorEntityDescription(
        key="emc_firmware",
        register_address=64,
        slave_id=0,
        data_type="string",
        string_count=16,
        has_entity_name=True,
    ),
    HagerFlowSensorEntityDescription(
        key="power_prioritaet_ziel",
        register_address=513,
        slave_id=0,
        data_type="uint16",
        device_class=SensorDeviceClass.ENUM,
        has_entity_name=True,
    ),
    HagerFlowSensorEntityDescription(
        key="power_prioritaet_entladung",
        register_address=513,
        slave_id=0,
        data_type="uint16",
        device_class=SensorDeviceClass.ENUM,
        has_entity_name=True,
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
        has_entity_name=True,
    ),
    HagerFlowSensorEntityDescription(
        key="emc_autarkie_letzte_stunde",
        register_address=4224,
        slave_id=0,
        data_type="uint16",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        has_entity_name=True,
    ),
    HagerFlowSensorEntityDescription(
        key="emc_eigenverbrauch_letzte_stunde",
        register_address=4225,
        slave_id=0,
        data_type="uint16",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        has_entity_name=True,
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
        has_entity_name=True,
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
        has_entity_name=True,
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
        has_entity_name=True,
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
        has_entity_name=True,
    ),
)

# 2. DYNAMIC METER TEMPLATES (Slaves 30-37)
METER_SENSOR_TEMPLATES: tuple[dict[str, any], ...] = (
    {"key_suffix": "leistung", "name_suffix": "Power", "addr": 4153, "type": "int32", "scale": 1.0, "unit": UnitOfPower.WATT, "device_class": SensorDeviceClass.POWER, "precision": 0},
    {"key_suffix": "leistung_l1", "name_suffix": "Power L1", "addr": 4155, "type": "int32", "scale": 1.0, "unit": UnitOfPower.WATT, "device_class": SensorDeviceClass.POWER, "precision": 0},
    {"key_suffix": "leistung_l2", "name_suffix": "Power L2", "addr": 4157, "type": "int32", "scale": 1.0, "unit": UnitOfPower.WATT, "device_class": SensorDeviceClass.POWER, "precision": 0},
    {"key_suffix": "leistung_l3", "name_suffix": "Power L3", "addr": 4159, "type": "int32", "scale": 1.0, "unit": UnitOfPower.WATT, "device_class": SensorDeviceClass.POWER, "precision": 0},
    {
        "key_suffix": "meter_type", 
        "name_suffix": "Type", 
        "addr": 4148, 
        "type": "uint16", 
        "scale": 1.0, 
        "unit": None, 
        "device_class": SensorDeviceClass.ENUM,
    },
)

# 3. DYNAMISCHE WALLBOX-VORLAGEN (Slaves 1-7)
WALLBOX_SENSOR_TEMPLATES: tuple[dict[str, any], ...] = (
    {"key_suffix": "firmware", "name_suffix": "Firmware", "addr": 4165, "type": "string", "count": 32, "scale": 1.0, "unit": None, "device_class": None},
    {"key_suffix": "ip_adresse", "name_suffix": "IP Address", "addr": 5385, "type": "string", "count": 8, "scale": 1.0, "unit": None, "device_class": None},
    {"key_suffix": "solar_leistung", "name_suffix": "Witty Solar Power", "addr": 5125, "type": "int16", "scale": 1.0, "unit": UnitOfPower.WATT, "device_class": SensorDeviceClass.POWER, "precision": 0},
    {"key_suffix": "gesamtenergie_geladen", "name_suffix": "Total Energy Charged", "addr": 4609, "type": "uint32", "scale": 0.001, "unit": "kWh", "device_class": SensorDeviceClass.ENERGY},
    {"key_suffix": "solarenergie_geladen", "name_suffix": "Solar Energy Charged", "addr": 4611, "type": "uint32", "scale": 0.001, "unit": "kWh", "device_class": SensorDeviceClass.ENERGY},
    {"key_suffix": "verbunden", "name_suffix": "Connected", "addr": 4613, "type": "uint16", "scale": 1.0, "unit": None, "device_class": None},
    {"key_suffix": "ladesession_badge", "name_suffix": "Charging Session Badge", "addr": 4929, "type": "string", "count": 16, "scale": 1.0, "unit": None, "device_class": None},
    {"key_suffix": "ladung_gesamt_session", "name_suffix": "Total Charge Current Session", "addr": 4950, "type": "uint32", "scale": 0.001, "unit": "kWh", "device_class": SensorDeviceClass.ENERGY},
    {"key_suffix": "ladung_netz_session", "name_suffix": "Grid Charge Current Session", "addr": 4952, "type": "uint32", "scale": 0.001, "unit": "kWh", "device_class": SensorDeviceClass.ENERGY},
    {"key_suffix": "ladung_pv_session", "name_suffix": "PV Charge Current Session", "addr": 4954, "type": "uint32", "scale": 0.001, "unit": "kWh", "device_class": SensorDeviceClass.ENERGY},
    {"key_suffix": "ladesession_rfid", "name_suffix": "Charging Session RFID Card", "addr": 5412, "type": "string", "count": 16, "scale": 1.0, "unit": None, "device_class": None},
)

# 4. DYNAMISCHE SG-READY-VORLAGEN (Slaves 50-59)
SG_READY_SENSOR_TEMPLATES: tuple[dict[str, any], ...] = (
    {
        "key_suffix": "sg_ready_status", 
        "name_suffix": "SG Ready Status", 
        "addr": 4152, 
        "type": "int32", 
        "scale": 1.0, 
        "unit": None, 
        "device_class": SensorDeviceClass.ENUM,
    },
)
