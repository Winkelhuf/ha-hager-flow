"""Sensor platform für ha_integration_domain."""
from typing import TYPE_CHECKING

from .descriptions import ENTITY_DESCRIPTIONS
from .entity import IntegrationBlueprintSensor

# Verhindert parallele Abfragen, da der Coordinator alles auf einmal holt
PARALLEL_UPDATES = 0

if TYPE_CHECKING:
    from custom_components.ha_integration_domain.data import IntegrationBlueprintConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: any,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Richte die Sensor-Plattform ein."""
    # Wir übergeben den Coordinator, die Beschreibung UND die einzigartige entry_id des Hubs
    async_add_entities(
        IntegrationBlueprintSensor(
            entry.runtime_data.coordinator, 
            description, 
            entry.entry_id
        ) 
        for description in ENTITY_DESCRIPTIONS
    )
