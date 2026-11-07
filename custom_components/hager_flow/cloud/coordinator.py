"""Coordinator für den optionalen Cloud-Zugang."""
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ..const import DOMAIN
from .api import CloudSnapshot, HagerFlowCloudApi
from .const import CLOUD_SCAN_INTERVAL
from .errors import HagerCloudError

_LOGGER = logging.getLogger(__name__)


class HagerFlowCloudCoordinator(DataUpdateCoordinator[CloudSnapshot]):
    """Liest Anlagen-Konfiguration und Wallboxen aus der Cloud (jede Minute).

    Fällt die Cloud aus, werden nur die Cloud-Entitäten unavailable –
    alle Modbus-Entitäten laufen unabhängig davon weiter.
    """

    def __init__(self, hass: HomeAssistant, api: HagerFlowCloudApi) -> None:
        super().__init__(hass, _LOGGER, name=f"{DOMAIN}_cloud", update_interval=CLOUD_SCAN_INTERVAL)
        self.api = api

    async def _async_update_data(self) -> CloudSnapshot:
        try:
            return await self.api.async_get_snapshot()
        except HagerCloudError as err:
            raise UpdateFailed(f"Hager flow Cloud: {err}") from err
