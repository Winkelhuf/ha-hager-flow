"""
Runtime data types for the Hager flow integration.

Access pattern: entry.runtime_data.client / entry.runtime_data.coordinator
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .coordinator import HagerFlowCoordinator


type IntegrationBlueprintConfigEntry = ConfigEntry["IntegrationBlueprintData"]


@dataclass
class IntegrationBlueprintData:
    """Runtime data stored on the config entry after a successful setup."""

    client: object
    coordinator: "HagerFlowCoordinator"
    integration: object
