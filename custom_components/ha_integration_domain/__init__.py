"""Die Hager flow Modbus Integration."""
from __future__ import annotations

import logging
from homeassistant.core import HomeAssistant
from .coordinator import HagerFlowCoordinator
from .data import IntegrationBlueprintConfigEntry

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: IntegrationBlueprintConfigEntry) -> bool:
    """Wird aufgerufen, wenn die Integration in der UI hinzugefügt wird."""
    
    # Holt die IP-Adresse (host), die du im Config-Flow eingibst
    host = entry.data.get("host")
    
    # Erstellt den Modbus-Coordinator mit deiner IP
    coordinator = HagerFlowCoordinator(hass, host=host)
    
    # Holt die ersten Daten direkt beim Start ab
    await coordinator.async_config_entry_first_refresh()
    
    # Speichert den Coordinator im Laufzeitspeicher von Home Assistant
    entry.runtime_data = IntegrationBlueprintConfigEntry(
        client=None, # Wird hier vom Template-Standard ignoriert
        coordinator=coordinator,
        integration=None,
    )
    
    # Leitet das Einrichten an die Sensor-Plattform weiter
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: IntegrationBlueprintConfigEntry) -> bool:
    """Wird aufgerufen, wenn die Integration gelöscht wird."""
    return await hass.config_entries.async_unload_platforms(entry, ["sensor"])
