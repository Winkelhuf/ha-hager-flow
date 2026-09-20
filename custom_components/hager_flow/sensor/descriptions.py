"""Sensor-Beschreibungen für die Hager flow Integration."""
from __future__ import annotations

from dataclasses import dataclass
from homeassistant.components.sensor import SensorEntityDescription, SensorStateClass, SensorDeviceClass
from homeassistant.const import UnitOfPower, PERCENTAGE

@dataclass(frozen=True, kw_only=True)
class HagerFlowSensorEntityDescription(SensorEntityDescription):
    """Beschreibung für ein Hager Flow Modbus Register."""
    register_address: int
    slave_id: int
    data_type: str
    scale: float = 1.0
    string_count: int = 1  # Standardmäßig 1 Register (2 Bytes) für numerische Werte

# 1. HAUPTSENSOREN (Immer vorhanden - Slave 0)
ENTITY_DESCRIPTIONS: tuple[HagerFlowSensorEntityDescription, ...] = (
    HagerFlowSensorEntityDescription(
        key="emc_seriennummer",
        name="Seriennummer",
        register_address=48,
        slave_id=0,
        data_type="string",
        string_count=16,
    ),
    HagerFlowSensorEntityDescription(
        key="emc_firmware",
        name="Firmware",
        register_address=64,
        slave_id=0,
        data_type="string",
        string_count=16,
    ),
    HagerFlowSensorEntityDescription(
        key="power_prioritaet_ziel",
        name="Ladepriorität",
        register_address=513,
        slave_id=0,
        data_type="uint16",
        device_class=SensorDeviceClass.ENUM,
        options=["Auto zuerst", "Batterie zuerst"],
    ),
    HagerFlowSensorEntityDescription(
        key="power_prioritaet_entladung",
        name="Batterieentladung ins Auto",
        register_address=513,
        slave_id=0,
        data_type="uint16",
        device_class=SensorDeviceClass.ENUM,
        options=["Verboten", "Erlaubt"],
    ),
    HagerFlowSensorEntityDescription(
        key="battery_power",
        name="Battery Power",
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
        name="Autarkie letzte Stunde",
        register_address=4224,
        slave_id=0,
        data_type="uint16",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    HagerFlowSensorEntityDescription(
        key="emc_eigenverbrauch_letzte_stunde",
        name="Eigenverbrauch letzte Stunde",
        register_address=4225,
        slave_id=0,
        data_type="uint16",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    HagerFlowSensorEntityDescription(
        key="pv_leistung_gesamt",
        name="PV Leistung Gesamt",
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
        name="Batterie SOC",
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
        name="Hausverbrauch Gesamt",
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
        name="Hausanschluss Leistung",
        register_address=4102,
        slave_id=0,
        data_type="int32",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
)

# 2. DYNAMISCHE METER-VORLAGEN (Slaves 30-37)
METER_SENSOR_TEMPLATES: tuple[dict[str, any], ...] = (
    {"key_suffix": "leistung", "name_suffix": "Leistung", "addr": 4153, "type": "int32", "scale": 1.0, "unit": UnitOfPower.WATT, "device_class": SensorDeviceClass.POWER, "precision": 0},
    {"key_suffix": "leistung_l1", "name_suffix": "Leistung L1", "addr": 4155, "type": "int32", "scale": 1.0, "unit": UnitOfPower.WATT, "device_class": SensorDeviceClass.POWER, "precision": 0},
    {"key_suffix": "leistung_l2", "name_suffix": "Leistung L2", "addr": 4157, "type": "int32", "scale": 1.0, "unit": UnitOfPower.WATT, "device_class": SensorDeviceClass.POWER, "precision": 0},
    {"key_suffix": "leistung_l3", "name_suffix": "Leistung L3", "addr": 4159, "type": "int32", "scale": 1.0, "unit": UnitOfPower.WATT, "device_class": SensorDeviceClass.POWER, "precision": 0},
    {
        "key_suffix": "meter_type", 
        "name_suffix": "Typ", 
        "addr": 4148, 
        "type": "uint16", 
        "scale": 1.0, 
        "unit": None, 
        "device_class": SensorDeviceClass.ENUM,
        "options": ["Undefiniert", "Hauptzähler (Root)", "Zusatzerzeugung", "Zusatzverbraucher", "Zusatzverbraucher Heizung/Klima", "Farm", "Ungenutzt", "Wallbox", "Farm Erweitert"]
    },
)

# 3. DYNAMISCHE WALLBOX-VORLAGEN (Slaves 1-7)
WALLBOX_SENSOR_TEMPLATES: tuple[dict[str, any], ...] = (
    {"key_suffix": "firmware", "name_suffix": "Firmware", "addr": 4165, "type": "string", "count": 32, "scale": 1.0, "unit": None, "device_class": None},
    {"key_suffix": "ip_adresse", "name_suffix": "IP Adresse", "addr": 5385, "type": "string", "count": 8, "scale": 1.0, "unit": None, "device_class": None},
    {"key_suffix": "solar_leistung", "name_suffix": "Witty Solar Leistung", "addr": 5125, "type": "int16", "scale": 1.0, "unit": UnitOfPower.WATT, "device_class": SensorDeviceClass.POWER, "precision": 0},
    {"key_suffix": "gesamtenergie_geladen", "name_suffix": "Gesamtenergie geladen", "addr": 4609, "type": "uint32", "scale": 0.001, "unit": "kWh", "device_class": SensorDeviceClass.ENERGY},
    {"key_suffix": "solarenergie_geladen", "name_suffix": "Solarenergie geladen", "addr": 4611, "type": "uint32", "scale": 0.001, "unit": "kWh", "device_class": SensorDeviceClass.ENERGY},
    {"key_suffix": "verbunden", "name_suffix": "Verbunden", "addr": 4613, "type": "uint16", "scale": 1.0, "unit": None, "device_class": None},
    {"key_suffix": "ladesession_badge", "name_suffix": "Ladesession Badge", "addr": 4929, "type": "string", "count": 16, "scale": 1.0, "unit": None, "device_class": None},
    {"key_suffix": "ladung_gesamt_session", "name_suffix": "Ladung Gesamt aktuelle Session", "addr": 4950, "type": "uint32", "scale": 0.001, "unit": "kWh", "device_class": SensorDeviceClass.ENERGY},
    {"key_suffix": "ladung_netz_session", "name_suffix": "Ladung Netz aktuelle Session", "addr": 4952, "type": "uint32", "scale": 0.001, "unit": "kWh", "device_class": SensorDeviceClass.ENERGY},
    {"key_suffix": "ladung_pv_session", "name_suffix": "Ladung PV aktuelle Session", "addr": 4954, "type": "uint32", "scale": 0.001, "unit": "kWh", "device_class": SensorDeviceClass.ENERGY},
    {"key_suffix": "ladesession_rfid", "name_suffix": "Ladesession RFID Karte", "addr": 5412, "type": "string", "count": 16, "scale": 1.0, "unit": None, "device_class": None},
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
        "options": ["Blockiert", "Normalbetrieb", "Anlaufempfehlung", "Anlaufbefehl"]
    },
)
