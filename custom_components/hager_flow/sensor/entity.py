"""Basis-Sensor-Klasse für Hager flow mit erzwungener Code-Live-Übersetzung."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from .descriptions import HagerFlowSensorEntityDescription
from ..entity.base import IntegrationBlueprintEntity

# Übersetzungstabelle für den SG Ready Status
SG_READY_MAPPING = {
    1: {"de": "Blockiert", "en": "Blocked"},
    2: {"de": "Normalbetrieb", "en": "Normal Operation"},
    3: {"de": "Anlaufempfehlung", "en": "Recommendation"},
    4: {"de": "Anlaufbefehl", "en": "Force Go"}
}

# Übersetzungstabelle für den PowerMeter Typ
METER_TYPE_MAPPING = {
    0: {"de": "Undefiniert", "en": "Undefined"},
    1: {"de": "Hauptzähler (Root)", "en": "Root Meter"},
    2: {"de": "Zusatzerzeugung", "en": "Additional Generation"},
    3: {"de": "Zusatzverbraucher", "en": "Additional Consumer"},
    4: {"de": "Zusatzverbraucher Heizung/Klima", "en": "Additional Consumer Heating/AC"},
    5: {"de": "Farm", "en": "Farm"},
    6: {"de": "Ungenutzt", "en": "Unused"},
    7: {"de": "Wallbox", "en": "Wallbox"},
    8: {"de": "Farm Erweitert", "en": "Farm Extended"}
}

# Feste Namen-Übersetzung für alle Sensoren (Verhindert das doppelte "Hager Flow EMC" auf dem Bild)
EXPLICIT_NAMES = {
    "emc_seriennummer": {"de": "Seriennummer", "en": "Serial Number"},
    "emc_firmware": {"de": "Firmware", "en": "Firmware"},
    "power_prioritaet_ziel": {"de": "Ladepriorität", "en": "Charging Priority"},
    "power_prioritaet_entladung": {"de": "Batterieentladung ins Auto", "en": "Battery Discharge into Car"},
    "battery_power": {"de": "Battery Power", "en": "Battery Power"},
    "emc_autarkie_letzte_stunde": {"de": "Autarkie letzte Stunde", "en": "Autarky Last Hour"},
    "emc_eigenverbrauch_letzte_stunde": {"de": "Eigenverbrauch letzte Stunde", "en": "Self-Consumption Last Hour"},
    "pv_leistung_gesamt": {"de": "PV Leistung Gesamt", "en": "Total PV Power"},
    "batterie_soc": {"de": "Batterie SOC", "en": "Battery SOC"},
    "hausverbrauch_gesamt": {"de": "Hausverbrauch Gesamt", "en": "Total House Consumption"},
    "hausanschluss_leistung": {"de": "Hausanschluss Leistung", "en": "Grid Power"},
    "leistung": {"de": "Leistung", "en": "Power"},
    "leistung_l1": {"de": "Leistung L1", "en": "Power L1"},
    "leistung_l2": {"de": "Leistung L2", "en": "Power L2"},
    "leistung_l3": {"de": "Leistung L3", "en": "Power L3"},
    "meter_type": {"de": "Typ", "en": "Type"},
    "firmware": {"de": "Firmware", "en": "Firmware"},
    "ip_adresse": {"de": "IP Adresse", "en": "IP Address"},
    "solar_leistung": {"de": "Witty Solar Leistung", "en": "Witty Solar Power"},
    "gesamtenergie_geladen": {"de": "Gesamtenergie geladen", "en": "Total Energy Charged"},
    "solarenergie_geladen": {"de": "Solarenergie geladen", "en": "Solar Energy Charged"},
    "verbunden": {"de": "Verbunden", "en": "Connected"},
    "ladesession_badge": {"de": "Ladesession Badge", "en": "Charging Session Badge"},
    "ladung_gesamt_session": {"de": "Ladung Gesamt aktuelle Session", "en": "Total Charge Current Session"},
    "ladung_netz_session": {"de": "Grid Charge aktuelle Session", "en": "Grid Charge Current Session"},
    "ladung_pv_session": {"de": "PV Charge aktuelle Session", "en": "PV Charge Current Session"},
    "ladesession_rfid": {"de": "Ladesession RFID Karte", "en": "Charging Session RFID Card"},
    "sg_ready_status": {"de": "SG Ready Status", "en": "SG Ready Status"}
}

class IntegrationBlueprintSensor(IntegrationBlueprintEntity, SensorEntity):
    """Repräsentiert einen Hager Modbus Sensor."""

    entity_description: HagerFlowSensorEntityDescription

    def __init__(self, coordinator, description: HagerFlowSensorEntityDescription, entry_id: str) -> None:
        """Initialisiere den Sensor."""
        super().__init__(coordinator, description, entry_id)
        self.entity_description = description

    @property
    def name(self) -> str | None:
        """Gibt den Namen der Entität LIVE basierend auf der aktuellen Benutzersprache zurück."""
        lang = self.hass.config.language if self.hass else "de"
        if lang not in ["de", "en"]:
            lang = "en"

        key_check: str = self.entity_description.key
        slave_id: int = getattr(self.entity_description, "slave_id", 0)

        # Suchschlüssel für den Klarnamen bereinigen
        lookup_key = key_check
        if key_check.startswith("meter_"):
            lookup_key = key_check.replace(f"meter_{slave_id}_", "")
        elif key_check.startswith("wb_"):
            lookup_key = key_check.replace(f"wb_{slave_id}_", "")
        elif key_check.startswith("sg_"):
            lookup_key = key_check.replace(f"sg_{slave_id}_", "")

        if lookup_key in EXPLICIT_NAMES:
            return EXPLICIT_NAMES[lookup_key][lang]
        return getattr(self.entity_description, "name", key_check)

    @property
    def options(self) -> list[str] | None:
        """Gibt die erlaubten ENUM-Optionen LIVE basierend auf der Benutzersprache zurück."""
        lang = self.hass.config.language if self.hass else "de"
        if lang not in ["de", "en"]:
            lang = "en"

        key_check: str = self.entity_description.key
        if "power_prioritaet_ziel" in key_check:
            return ["Auto zuerst", "Batterie zuerst"] if lang == "de" else ["Car First", "Battery First"]
        elif "power_prioritaet_entladung" in key_check:
            return ["Verboten", "Erlaubt"] if lang == "de" else ["Forbidden", "Allowed"]
        elif "meter_type" in key_check:
            return [m[lang] for m in METER_TYPE_MAPPING.values()]
        elif "sg_ready_status" in key_check:
            return [s[lang] for s in SG_READY_MAPPING.values()]
        return None

    @property
    def native_value(self) -> any:
        """Gibt den übersetzten Zustand direkt und live zurück."""
        raw_value = self.coordinator.data.get(self.entity_description.key)
        
        if raw_value is None:
            return None

        lang = self.hass.config.language if self.hass else "de"
        if lang not in ["de", "en"]:
            lang = "en"

        if "sg_ready_status" in self.entity_description.key:
            return SG_READY_MAPPING.get(int(raw_value), {"de": "Unbekannt", "en": "Unknown"})[lang]

        if "meter_type" in self.entity_description.key:
            return METER_TYPE_MAPPING.get(int(raw_value), {"de": "Unbekannt", "en": "Unknown"})[lang]

        if self.entity_description.key == "power_prioritaet_ziel":
            bit_0 = int(raw_value) & 0x01
            if lang == "de":
                return "Batterie zuerst" if bit_0 == 1 else "Auto zuerst"
            return "Battery First" if bit_0 == 1 else "Car First"

        if self.entity_description.key == "power_prioritaet_entladung":
            bit_1 = (int(raw_value) >> 1) & 0x01
            if lang == "de":
                return "Erlaubt" if bit_1 == 1 else "Verboten"
            return "Allowed" if bit_1 == 1 else "Forbidden"

        return raw_value
