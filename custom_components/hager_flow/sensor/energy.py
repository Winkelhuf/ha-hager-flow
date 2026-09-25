"""Energiesensoren, die aus den vorhandenen Leistungswerten (W) per Trapezregel
zu kWh integriert werden.

Der Hager EMC liefert für PV-Gesamtleistung, Hausverbrauch, Netzleistung und
Batterieleistung nur Momentanwerte (W), aber keine eigenen Energiezähler-Register.
Für das Home Assistant Energie-Dashboard werden jedoch state_class TOTAL_INCREASING
bzw. TOTAL Sensoren in kWh benötigt. Diese Datei erzeugt solche Sensoren automatisch
aus den bestehenden Leistungssensoren – ganz ohne manuell in Home Assistant
anzulegende "Riemann-Summe"-Hilfssensoren.

Signierte Leistungswerte (Netzanschluss, Batterie) werden dabei in je einen
"positiven" und einen "negativen" Energiesensor aufgeteilt (z.B. Netzbezug /
Netzeinspeisung), wie es das Energie-Dashboard erwartet.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy
from homeassistant.util import dt as dt_util

from ..entity.base import HagerFlowEntity


@dataclass(frozen=True, kw_only=True)
class HagerFlowEnergyEntityDescription(SensorEntityDescription):
    """Beschreibt einen aus einem Leistungswert integrierten Energiesensor."""

    source_key: str
    """Key des zugrunde liegenden Leistungssensors (W) in coordinator.data."""

    direction: str = "total"
    """"total": kompletter Wert wird integriert (immer positive Leistung).
    "positive": nur der positive Anteil der (ggf. vorzeichenbehafteten) Leistung.
    "negative": nur der negative Anteil, als positive Energie ausgegeben."""

    slave_id: int = 0
    """Nur für dynamisch erkannte Geräte gesetzt, damit HagerFlowEntity den
    Sensor dem richtigen (Unter-)Gerät zuordnet (siehe entity/base.py)."""


# Aus welchen Leistungssensoren sollen zusätzliche Energiesensoren (kWh)
# abgeleitet werden? source_key muss ein Key aus ENTITY_DESCRIPTIONS sein.
ENERGY_ENTITY_DESCRIPTIONS: tuple[HagerFlowEnergyEntityDescription, ...] = (
    HagerFlowEnergyEntityDescription(
        key="pv_energie_gesamt",
        source_key="pv_leistung_gesamt",
        direction="total",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
    ),
    HagerFlowEnergyEntityDescription(
        key="hausverbrauch_energie",
        source_key="hausverbrauch_gesamt",
        direction="total",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
    ),
    HagerFlowEnergyEntityDescription(
        key="netzbezug_energie",
        source_key="hausanschluss_leistung",
        direction="positive",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
    ),
    HagerFlowEnergyEntityDescription(
        key="netzeinspeisung_energie",
        source_key="hausanschluss_leistung",
        direction="negative",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
    ),
    HagerFlowEnergyEntityDescription(
        key="batterie_ladung_energie",
        source_key="battery_power",
        direction="positive",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
    ),
    HagerFlowEnergyEntityDescription(
        key="batterie_entladung_energie",
        source_key="battery_power",
        direction="negative",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
    ),
)


# Dynamische Zähler (Slaves 30-37, siehe METER_SENSOR_TEMPLATES) liefern nur
# "leistung" (W), aber ebenfalls kein eigenes Energie-Register. Da der
# Zähler-Typ (Root/Zusatzerzeugung/Zusatzverbraucher/...) das Vorzeichen der
# Leistung bestimmt und wir das nicht pauschal kennen, wird die Leistung –
# wie bei Netzbezug/-einspeisung – generisch in einen "Bezug"- und einen
# "Einspeisung"-Energiesensor aufgeteilt. Bei einem reinen Verbraucher-Zähler
# bleibt der Einspeisung-Sensor einfach bei 0 kWh, bei einem
# Erzeugung-Zähler entsprechend der Bezug-Sensor.
METER_ENERGY_TEMPLATES: tuple[dict[str, str], ...] = (
    {"key_suffix": "energie_bezug", "direction": "positive"},
    {"key_suffix": "energie_einspeisung", "direction": "negative"},
)


def build_meter_energy_description(slave: int, key_suffix: str, direction: str) -> HagerFlowEnergyEntityDescription:
    """Erzeuge die Energie-Beschreibung für einen dynamisch erkannten Zähler.

    Wird von sensor/__init__.py für jeden per Auto-Discovery gefundenen
    Zähler (Slaves 30-37) aufgerufen – dadurch entstehen automatisch auch
    für neu hinzukommende Zähler passende kWh-Sensoren, ohne Code-Änderung.
    """
    return HagerFlowEnergyEntityDescription(
        key=f"meter_{slave}_{key_suffix}",
        source_key=f"meter_{slave}_leistung",
        slave_id=slave,
        direction=direction,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
    )


class HagerFlowEnergySensor(HagerFlowEntity, RestoreSensor):
    """Integriert einen Leistungssensor (W) per Trapezregel zu einem kWh-Zähler.

    Läuft rein lokal im Coordinator-Takt (alle 5s), benötigt also keine
    zusätzlichen Modbus-Register. Der Zählerstand wird über Neustarts hinweg
    per RestoreSensor wiederhergestellt, damit das Energie-Dashboard
    lückenlose Tageswerte berechnen kann.
    """

    entity_description: HagerFlowEnergyEntityDescription
    _attr_should_poll = False

    def __init__(self, coordinator, description: HagerFlowEnergyEntityDescription, entry_id: str) -> None:
        """Initialisiere den Energiesensor."""
        super().__init__(coordinator, description, entry_id)
        self._accumulated_kwh: float = 0.0
        self._last_update: datetime | None = None
        self._last_power: float | None = None

    async def async_added_to_hass(self) -> None:
        """Beim Hinzufügen den zuletzt bekannten Zählerstand wiederherstellen.

        Die eigentliche Listener-Registrierung beim Coordinator übernimmt bereits
        CoordinatorEntity.async_added_to_hass() weiter oben in der MRO-Kette
        (über super()) – hier wird sie NICHT zusätzlich vorgenommen, sonst würde
        _handle_coordinator_update doppelt aufgerufen und die Energie doppelt gezählt.
        """
        await super().async_added_to_hass()

        last_data = await self.async_get_last_sensor_data()
        if last_data is not None and last_data.native_value is not None:
            try:
                self._accumulated_kwh = float(last_data.native_value)
            except (TypeError, ValueError):
                self._accumulated_kwh = 0.0

        self._last_update = dt_util.utcnow()

    @property
    def native_value(self) -> float:
        """Aktueller Zählerstand in kWh."""
        return round(self._accumulated_kwh, 4)

    def _handle_coordinator_update(self) -> None:
        """Neuen Leistungswert einlesen und die Energie fortschreiben."""
        power = self.coordinator.data.get(self.entity_description.source_key)
        now = dt_util.utcnow()

        if power is not None and self._last_power is not None and self._last_update is not None:
            elapsed_hours = (now - self._last_update).total_seconds() / 3600
            if 0 < elapsed_hours < 1:  # Ausreißer nach z.B. HA-Neustart ignorieren
                avg_power = (power + self._last_power) / 2

                direction = self.entity_description.direction
                if direction == "positive":
                    avg_power = max(avg_power, 0.0)
                elif direction == "negative":
                    avg_power = -min(avg_power, 0.0)

                self._accumulated_kwh += (avg_power * elapsed_hours) / 1000

        if power is not None:
            self._last_power = power
        self._last_update = now

        self.async_write_ha_state()
