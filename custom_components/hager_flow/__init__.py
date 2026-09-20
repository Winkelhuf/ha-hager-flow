"""Die Hager flow Modbus Integration."""
from __future__ import annotations

import logging
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from .coordinator import HagerFlowCoordinator
from .data import IntegrationBlueprintConfigEntry, IntegrationBlueprintData

_LOGGER = logging.getLogger(__name__)

# Hier definieren wir, welche Plattformdateien Home Assistant laden soll
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]

async def async_setup_entry(hass: HomeAssistant, entry: IntegrationBlueprintConfigEntry) -> bool:
    """Wird aufgerufen, wenn die Integration in Home Assistant geladen wird."""
    host = entry.data.get("host")

    # Erstellt deinen funktionierenden Modbus-Coordinator
    coordinator = HagerFlowCoordinator(hass, host)
    
    # Erste Gerätesuche und Datenabruf durchführen
    await coordinator.async_config_entry_first_refresh()

    # Befüllen von runtime_data mit Client und Coordinator
    entry.runtime_data = IntegrationBlueprintData(
        client=None,
        coordinator=coordinator,
        integration=None,
    )

    # Schaltet die Plattformen (sensor.py und unsere neue switch.py) aktiv
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: IntegrationBlueprintConfigEntry) -> bool:
    """Wird aufgerufen, wenn die Integration entfernt oder neu geladen wird."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
