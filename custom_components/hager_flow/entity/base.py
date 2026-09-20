"""Basis-Entitätsklasse für die Hager flow Integration."""

from typing import TYPE_CHECKING
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

if TYPE_CHECKING:
    from homeassistant.helpers.entity import EntityDescription
    from ..coordinator.base import HagerFlowCoordinator

class IntegrationBlueprintEntity(CoordinatorEntity["HagerFlowCoordinator"]):
    """Basis-Entität, die Geräteinformationen, eine eindeutige ID und Icons bereitstellt."""

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
        
        # Generiert eine saubere, dauerhafte Unique ID für Home Assistant
        self._attr_unique_id = f"{entry_id}_{entity_description.key}"
        
        # Ermittle den Typ des Sensors anhand des Keys für eine smarte Geräte-Gruppierung
        key: str = entity_description.key
        slave_id: int = getattr(entity_description, "slave_id", 0)

        # Standard-Gerät (Der Hager EMC R3 Haupt-Controller)
        device_key = f"hager_flow_emc_{entry_id}"
        device_name = "Hager Flow EMC"
        device_model = "EMC R3"

        # Dynamische Gruppierung für zusätzliche Untergeräte (Zähler, Wallboxen, SG Ready)
        if key.startswith("meter_"):
            device_key = f"hager_flow_meter_{slave_id}_{entry_id}"
            device_name = coordinator.discovered_meters.get(slave_id, f"Hager Zähler (Slave {slave_id})")
            device_model = "Powermeter RTU"
        elif key.startswith("wb_"):
            device_key = f"hager_flow_wb_{slave_id}_{entry_id}"
            device_name = coordinator.discovered_wallboxes.get(slave_id, f"Witty Wallbox (Slave {slave_id})")
            device_model = "Witty Wallbox"
        elif key.startswith("sg_"):
            device_key = f"hager_flow_sg_{slave_id}_{entry_id}"
            device_name = coordinator.discovered_sg_ready.get(slave_id, f"SG Ready (Slave {slave_id})")
            device_model = "SG Ready Schnittstelle"

        # Zuweisung der Geräte-Informationen für die UI-Ansicht
        self._attr_device_info = DeviceInfo(
            identifiers={("hager_flow", device_key)},
            name=device_name,
            manufacturer="Hager",
            model=device_model,
        )
