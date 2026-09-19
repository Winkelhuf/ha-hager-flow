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
    
    coordinator = HagerFlowCoordinator(hass, host=host)
    await coordinator.async_config_entry_first_refresh()
    
    entry.runtime_data = IntegrationBlueprintConfigEntry(
        client=None,
        coordinator=coordinator,
        integration=None,
    )
    
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: IntegrationBlueprintConfigEntry) -> bool:
    """Wird aufgerufen, wenn die Integration gelöscht wird."""
    return await hass.config_entries.async_unload_platforms(entry, ["sensor"])
