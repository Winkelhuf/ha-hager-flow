"""Die Hager flow Modbus Integration."""
from __future__ import annotations

import logging
from homeassistant.core import HomeAssistant
from .coordinator import HagerFlowCoordinator
from .data import IntegrationBlueprintConfigEntry

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: IntegrationBlueprintConfigEntry) -> bool:
    """Wird aufgerufen, wenn die Integration in der UI hinzugefügt wird."""
    host = entry.data.get("host")
    
    # Erstellt deinen funktionierenden Modbus-Coordinator
    coordinator = HagerFlowCoordinator(hass, host=host)
    await coordinator.async_config_entry_first_refresh()
    
    # Der korrekte Weg für Home Assistant ab 2024+: 
    # Wir befüllen runtime_data direkt mit dem Daten-Objekt!
    from .data import IntegrationBlueprintData
    entry.runtime_data = IntegrationBlueprintData(
        client=None,
        coordinator=coordinator,
        integration=None,
    )
    
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True
