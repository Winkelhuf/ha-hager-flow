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
    DEFAULT_DISCHARGE_SOC_ON_ENABLE,
)
from .errors import HagerCloudError

_LOGGER = logging.getLogger(__name__)

# Nicht öfter als alle 25 s automatisch korrigieren (Schutz vor Dauerschreiben)
_GUARD_MIN_INTERVAL = 25.0

# So lange (Sekunden) werden anhaltende Cloud-Lesefehler überbrückt – der letzte Stand
# bleibt sichtbar, bevor die Entitäten auf "unavailable" gehen. Deckt auch längere
# Lab-Aussetzer ab (z. B. HTTP 400 "invalid response output" während eines config/sync).
_MAX_CLOUD_ERROR_DURATION = 300.0


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
        # Vorheriger Zustand "Entladung ins Auto aktiv" (None = noch unbekannt/Startzustand),
        # um das Aktivieren zu erkennen und die Standard-Entladegrenze zu setzen.
        self._discharge_was_on: bool | None = None
        # Zeitpunkt des ersten einer Serie von Cloud-Lesefehlern (für die Fehlertoleranz)
        self._first_error_at: float | None = None
        # True, solange nur noch der letzte (gehaltene) Stand geliefert wird (Cloud gestört).
        # Entitäten nutzen das, um das aggressive Nachpollen zurückzufahren.
        self.degraded = False

    @staticmethod
    def _discharge_enabled(config: dict) -> bool:
        return not config.get(CFG_BATTERY_BEFORE_CAR, False) and (
            config.get(CFG_BATTERY_TO_CAR_SOLAR, False) or config.get(CFG_BATTERY_TO_CAR_BOOST, False)
        )

    def note_discharge_target(self, soc: int) -> None:
        """Merkt sich den vom Nutzer gesetzten Entlade-Zielwert (für die Auto-Korrektur)."""
        self._desired_discharge_soc = int(soc)

    async def _async_update_data(self) -> CloudSnapshot:
        try:
            snapshot = await self.api.async_get_snapshot()
        except HagerCloudError as err:
            # Transiente Cloud-Fehler (z. B. sporadisches HTTP 400 der Lab-Umgebung)
            # nicht sofort auf alle Entitäten durchschlagen lassen: kurz den letzten
            # Stand halten und erst nach mehreren Fehlversuchen "unavailable" melden.
            now = time.monotonic()
            if self._first_error_at is None:
                self._first_error_at = now
            if self.data is not None and (now - self._first_error_at) < _MAX_CLOUD_ERROR_DURATION:
                self.degraded = True
                _LOGGER.warning(
                    "Cloud-Lesefehler seit %.0fs – behalte vorerst den letzten Stand: %s",
                    now - self._first_error_at,
                    err,
                )
                return self.data
            raise UpdateFailed(f"Hager flow Cloud: {err}") from err
        self._first_error_at = None
        self.degraded = False
        await self._async_apply_discharge_default_on_enable(snapshot)
        await self._async_guard_discharge_limit(snapshot)
        return snapshot

    async def _async_apply_discharge_default_on_enable(self, snapshot: CloudSnapshot) -> None:
        """Beim Aktivieren der Entladung ins Auto die Entladegrenze auf den Standard setzen.

        So wird direkt nach dem Einschalten zunächst (nahezu) nicht entladen, bis der Nutzer
        aktiv einen niedrigeren Wert wählt. Ein bereits höherer Wert (weniger Entladung) bleibt.
        """
        discharge_on = self._discharge_enabled(snapshot.config)
        prev, self._discharge_was_on = self._discharge_was_on, discharge_on
        # Nur beim echten Übergang aus→an reagieren (nicht beim Start und nicht dauernd)
        if prev is None or not discharge_on or prev or snapshot.emc_serial is None:
            return
        floor = min_discharge_soc(snapshot.reserve_wh, snapshot.capacity_wh)
        default = min(100, max(floor, DEFAULT_DISCHARGE_SOC_ON_ENABLE))
        current = max(
            (wb.discharge_soc for wb in snapshot.wallboxes.values() if wb.discharge_soc is not None),
            default=None,
        )
        # Ist der aktuelle Wert schon >= Standard (also wenig/keine Entladung), nichts tun
        if current is not None and current >= default:
            self._desired_discharge_soc = current
            return
        try:
            await self.api.async_set_discharge_soc(snapshot.emc_serial, snapshot.config, default)
        except HagerCloudError as err:
            _LOGGER.debug("Standard-Entladegrenze konnte nicht gesetzt werden: %s", err)
            return
        for wb in snapshot.wallboxes.values():
            if wb.discharge_soc is not None:
                wb.discharge_soc = default
        self._desired_discharge_soc = default
        _LOGGER.info(
            "Entladung ins Auto aktiviert – Entladegrenze auf Standard %s %% gesetzt", default
        )

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
