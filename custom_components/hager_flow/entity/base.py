"""Basis-Entitätsklasse für die Hager flow Integration."""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

if TYPE_CHECKING:
    from homeassistant.helpers.entity import EntityDescription
    from ..coordinator.base import HagerFlowCoordinator

# Dynamische Keys: meter_30_leistung_l1, wb_1_firmware, sg_50_sg_ready_status ...
_DYNAMIC_KEY = re.compile(r"^(?:meter|wb|sg)_\d+_(?P<suffix>.+)$")


def translation_key_for(key: str) -> str:
    """
    Liefere den Übersetzungs-Key zu einem Entity-Key.

    Der Übersetzungs-Key gehört zum Entitäts-TYP, nicht zum einzelnen Slave:
    ``meter_30_leistung_l1`` und ``meter_31_leistung_l1`` nutzen beide
    ``leistung_l1``. Statische Keys (``batterie_soc``) bleiben unverändert.
    """
    match = _DYNAMIC_KEY.match(key)
    return match["suffix"] if match else key


class HagerFlowEntity(CoordinatorEntity["HagerFlowCoordinator"]):
    """Basis-Entität, die Geräteinformationen, eine eindeutige ID und Übersetzungen bereitstellt."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: "HagerFlowCoordinator",
        entity_description: EntityDescription,
        entry_id: str,
    ) -> None:
        """Initialisierung der Entität."""
        super().__init__(coordinator)
        self.entity_description = entity_description

        key: str = entity_description.key
        slave_id: int = getattr(entity_description, "slave_id", 0)

        # Unique ID: unverändert (inkl. Slave-ID), damit bestehende Entitäten
        # samt Verlauf erhalten bleiben. Sie hängt NICHT am translation_key.
        self._attr_unique_id = f"{entry_id}_{key}"

        # Der Name kommt ausschließlich aus translations/<sprache>.json
        # (entity.<plattform>.<translation_key>.name). Home Assistant setzt
        # den Gerätenamen ("Garage") wegen has_entity_name automatisch davor.
        self._attr_translation_key = translation_key_for(key)

        # Standard-Gerät (Der Hager EMC R3 Haupt-Controller)
        device_key = f"hager_flow_emc_{entry_id}"
        device_name = "Hager Flow EMC"
        device_model = "EMC R3"

        # Dynamische Gruppierung für Untergeräte (Zähler, Wallboxen, SG Ready).
        # Der Gerätename ist der live aus dem Gerät gelesene Klarname.
        if key.startswith("meter_"):
            device_key = f"hager_flow_meter_{slave_id}_{entry_id}"
            device_name = coordinator.discovered_meters.get(slave_id, f"Modbus {slave_id}")
            device_model = "Powermeter RTU"
        elif key.startswith("wb_"):
            device_key = f"hager_flow_wb_{slave_id}_{entry_id}"
            device_name = coordinator.discovered_wallboxes.get(slave_id, f"Modbus {slave_id}")
            device_model = "Witty Wallbox"
        elif key.startswith("sg_"):
            device_key = f"hager_flow_sg_{slave_id}_{entry_id}"
            device_name = coordinator.discovered_sg_ready.get(slave_id, f"Modbus {slave_id}")
            device_model = "SG Ready interface"

        # Zuweisung der Geräte-Informationen für die UI-Ansicht
        self._attr_device_info = DeviceInfo(
            identifiers={("hager_flow", device_key)},
            name=device_name,
            manufacturer="Hager",
            model=device_model,
        )