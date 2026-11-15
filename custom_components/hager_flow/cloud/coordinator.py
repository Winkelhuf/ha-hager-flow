"""Coordinator für den optionalen Cloud-Zugang."""
from __future__ import annotations

import logging
import time

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ..const import DOMAIN
from .api import CloudSnapshot, HagerFlowCloudApi, guard_discharge_target, min_discharge_soc
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
        # Zuletzt gewünschtes Entladelimit (>= Untergrenze); wird bei einem Sync-Reset
        # wiederhergestellt, damit ein höher gesetzter Wert nicht verloren geht.
        self._desired_discharge_soc: int | None = None

    def note_discharge_target(self, soc: int) -> None:
        """Merkt sich den vom Nutzer gesetzten Entlade-Zielwert (für die Auto-Korrektur)."""
        self._desired_discharge_soc = int(soc)

    async def _async_update_data(self) -> CloudSnapshot:
        try:
            snapshot = await self.api.async_get_snapshot()
        except HagerCloudError as err:
            raise UpdateFailed(f"Hager flow Cloud: {err}") from err
        await self._async_guard_discharge_limit(snapshot)
        return snapshot

    async def _async_guard_discharge_limit(self, snapshot: CloudSnapshot) -> None:
        """Wächter für das Entladelimit ("Bis Ladezustand").

        Zwei Aufgaben:
        1. Das Limit darf nie unter die Reserve-Untergrenze fallen.
        2. Ein vom Nutzer höher gesetzter Wert (z. B. 85 %) darf nicht nachträglich auf
           die Untergrenze heruntergezogen werden.

        Das ``config/sync`` beim Reserve-/Config-Schreiben setzt das Limit am Gerät
        zeitverzögert auf 0 zurück. Der Coordinator merkt sich den zuletzt gültigen
        Wunschwert (>= Untergrenze) und stellt genau diesen bei einem Reset wieder her.
        """
        config = snapshot.config
        discharge_on = not config.get(CFG_BATTERY_BEFORE_CAR, False) and (
            config.get(CFG_BATTERY_TO_CAR_SOLAR, False) or config.get(CFG_BATTERY_TO_CAR_BOOST, False)
        )
        if not discharge_on or snapshot.emc_serial is None:
            return
        floor = min_discharge_soc(snapshot.reserve_wh, snapshot.capacity_wh)

        # loading-priorisation ist systemweit – alle Wallboxen teilen sich einen Wert
        current = max(
            (wb.discharge_soc for wb in snapshot.wallboxes.values() if wb.discharge_soc is not None),
            default=None,
        )
        self._desired_discharge_soc, target = guard_discharge_target(
            current, self._desired_discharge_soc, floor
        )
        if target is None:
            return
        now = time.monotonic()
        if now - self._last_guard_fix < _GUARD_MIN_INTERVAL:
            return
        self._last_guard_fix = now
        try:
            await self.api.async_set_discharge_soc(snapshot.emc_serial, config, target)
        except HagerCloudError as err:
            _LOGGER.debug("Auto-Korrektur des Entladelimits fehlgeschlagen: %s", err)
            return
        for wb in snapshot.wallboxes.values():
            if wb.discharge_soc is not None:
                wb.discharge_soc = target
        _LOGGER.info(
            "Entladelimit lag unter der Reserve-Untergrenze – automatisch auf %s %% zurückgesetzt", target
        )
