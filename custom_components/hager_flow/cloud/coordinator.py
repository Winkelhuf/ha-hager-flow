"""Coordinator für den optionalen Cloud-Zugang."""
from __future__ import annotations

import logging
import time

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ..const import DOMAIN
from .api import CloudSnapshot, HagerFlowCloudApi, min_discharge_soc
from .const import (
    CFG_BATTERY_BEFORE_CAR,
    CFG_BATTERY_TO_CAR_BOOST,
    CFG_BATTERY_TO_CAR_SOLAR,
    CLOUD_SCAN_INTERVAL,
)
from .errors import HagerCloudError

_LOGGER = logging.getLogger(__name__)

# Nicht öfter als alle 25 s automatisch korrigieren (Schutz vor Dauerschreiben)
_GUARD_MIN_INTERVAL = 25.0


class HagerFlowCloudCoordinator(DataUpdateCoordinator[CloudSnapshot]):
    """Liest Anlagen-Konfiguration und Wallboxen aus der Cloud (jede Minute).

    Fällt die Cloud aus, werden nur die Cloud-Entitäten unavailable –
    alle Modbus-Entitäten laufen unabhängig davon weiter.
    """

    def __init__(self, hass: HomeAssistant, api: HagerFlowCloudApi) -> None:
        super().__init__(hass, _LOGGER, name=f"{DOMAIN}_cloud", update_interval=CLOUD_SCAN_INTERVAL)
        self.api = api
        self._last_guard_fix = 0.0

    async def _async_update_data(self) -> CloudSnapshot:
        try:
            snapshot = await self.api.async_get_snapshot()
        except HagerCloudError as err:
            raise UpdateFailed(f"Hager flow Cloud: {err}") from err
        await self._async_guard_discharge_limit(snapshot)
        return snapshot

    async def _async_guard_discharge_limit(self, snapshot: CloudSnapshot) -> None:
        """Wächter: das Entladelimit darf nie unter die Reserve-Untergrenze fallen.

        Das ``config/sync`` beim Reserve-Schreiben setzt das Limit am Gerät zeitverzögert
        auf 0 zurück. Wird hier ein zu niedriges Limit erkannt (bei aktiver Entladung),
        hebt der Coordinator es einmalig wieder auf die Untergrenze an.
        """
        config = snapshot.config
        discharge_on = not config.get(CFG_BATTERY_BEFORE_CAR, False) and (
            config.get(CFG_BATTERY_TO_CAR_SOLAR, False) or config.get(CFG_BATTERY_TO_CAR_BOOST, False)
        )
        if not discharge_on or snapshot.emc_serial is None:
            return
        floor = min_discharge_soc(snapshot.reserve_wh, snapshot.capacity_wh)
        too_low = [
            wb for wb in snapshot.wallboxes.values() if wb.discharge_soc is not None and wb.discharge_soc < floor
        ]
        if not too_low:
            return
        now = time.monotonic()
        if now - self._last_guard_fix < _GUARD_MIN_INTERVAL:
            return
        self._last_guard_fix = now
        try:
            # loading-priorisation ist systemweit – ein Schreibvorgang genügt
            await self.api.async_set_discharge_soc(snapshot.emc_serial, config, floor)
        except HagerCloudError as err:
            _LOGGER.debug("Auto-Korrektur des Entladelimits fehlgeschlagen: %s", err)
            return
        for wb in too_low:
            wb.discharge_soc = floor
        _LOGGER.info(
            "Entladelimit lag unter der Reserve-Untergrenze – automatisch auf %s %% angehoben", floor
        )
