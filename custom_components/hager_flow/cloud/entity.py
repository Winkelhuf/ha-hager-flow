"""Basis-Entität für Cloud-Funktionen.

Cloud-Entitäten hängen sich an die bestehenden Modbus-Geräte (EMC bzw. Wallbox),
damit Lesen (Modbus) und Schreiben (Cloud) im selben Gerät erscheinen.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
import logging
from typing import Any

from homeassistant.const import EntityCategory
from homeassistant.core import callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from .api import CloudWallbox
from .const import CLOUD_CONFIRM_INTERVAL, CLOUD_COOLDOWN, CLOUD_DEBOUNCE
from .coordinator import HagerFlowCloudCoordinator
from .errors import HagerCloudError

_LOGGER = logging.getLogger(__name__)


def emc_device_info(entry_id: str) -> DeviceInfo:
    """Dasselbe EMC-Gerät wie in entity/base.py (Plattformen starten parallel, daher vollständig)."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"hager_flow_emc_{entry_id}")},
        name="Hager Flow EMC",
        manufacturer="Hager",
        model="EMC R3",
    )


def wallbox_device_info(entry_id: str, wallbox: CloudWallbox, modbus_wallboxes: dict[int, str]) -> DeviceInfo:
    """Ordnet die Cloud-Wallbox über den Namen der Modbus-Wallbox zu, sonst eigenes Gerät."""
    wanted = wallbox.name.strip().casefold()
    for slave, name in modbus_wallboxes.items():
        if name.strip().casefold() == wanted:
            return DeviceInfo(
                identifiers={(DOMAIN, f"hager_flow_wb_{slave}_{entry_id}")},
                name=name,
                manufacturer="Hager",
                model="Witty Wallbox",
            )
    return DeviceInfo(
        identifiers={(DOMAIN, f"hager_flow_cloud_wb_{wallbox.evse_id}_{entry_id}")},
        name=wallbox.name or f"Wallbox {wallbox.evse_id}",
        manufacturer="Hager",
        model="Witty Wallbox",
        via_device=(DOMAIN, f"hager_flow_emc_{entry_id}"),
    )


class HagerFlowCloudEntity(CoordinatorEntity[HagerFlowCloudCoordinator]):
    """Gemeinsame Logik: Name aus translations, Kategorie Konfiguration, Klickschutz, Fehler.

    Die Cloud braucht bis zu ~30 s, bis eine Änderung am Gerät angekommen und wieder
    zurückgemeldet ist. Solange zeigt die Entität den gewählten Wert (optimistisch) und
    weist weitere Klicks mit einer Meldung ab – wie der Boost-Schalter der Wallbox.
    """

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: HagerFlowCloudCoordinator, entry_id: str, key: str, device_info: DeviceInfo) -> None:
        super().__init__(coordinator)
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry_id}_cloud_{key}"
        self._attr_device_info = device_info
        self._optimistic: Any = None
        self._cooldown_until: datetime | None = None
        # Laufender Schreibbefehl im Sammelfenster (letzter Klick gewinnt)
        self._pending: tuple[Callable[[], Awaitable[None]], Any] | None = None
        self._debounce_unsub: Callable[[], None] | None = None
        # Nachpoll-Timer, bis das Gerät den geschriebenen Wert bestätigt
        self._confirm_unsub: Callable[[], None] | None = None

    def _read_actual(self) -> Any:
        """Von der Unterklasse: der aktuell vom Gerät gemeldete Wert (zum Abgleich mit
        dem optimistischen Wunschwert). Standard: keine Bestätigungserkennung."""
        return None

    @callback
    def _handle_coordinator_update(self) -> None:
        # Hat das Gerät den gewünschten Wert übernommen, endet die Maske/Sperre sofort.
        if (
            self._cooling_down
            and self._pending is None
            and self._optimistic is not None
            and self._read_actual() == self._optimistic
        ):
            self._cooldown_until = None
        super()._handle_coordinator_update()

    @property
    def _cooling_down(self) -> bool:
        return self._cooldown_until is not None and datetime.now() < self._cooldown_until

    def _value(self, actual: Any) -> Any:
        """Im Sammelfenster und während der Sperre den gewählten Wert zeigen, sonst den echten."""
        return self._optimistic if (self._pending is not None or self._cooling_down) else actual

    async def _async_write(self, action: Callable[[], Awaitable[None]], optimistic: Any) -> None:
        """Klick entgegennehmen: im 1,5-s-Sammelfenster nur den Wert übernehmen und den
        Timer neu starten; erst danach wird einmal in die Cloud geschrieben. Während der
        30-s-Sperre nach einem Schreibvorgang werden weitere Klicks mit Hinweis abgewiesen."""
        if self._cooling_down:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="cloud_cooldown",
                translation_placeholders={
                    "seconds": str(int((self._cooldown_until - datetime.now()).total_seconds()) + 1)
                },
            )
        # Wert sofort anzeigen und den Schreibbefehl bis zum Ende des Sammelfensters zurückstellen
        self._optimistic = optimistic
        self._pending = (action, optimistic)
        self.async_write_ha_state()
        if self._debounce_unsub is not None:
            self._debounce_unsub()
        self._debounce_unsub = async_call_later(
            self.hass, CLOUD_DEBOUNCE.total_seconds(), self._async_commit
        )

    async def _async_commit(self, _now: Any = None) -> None:
        """Nach Ablauf des Sammelfensters den zuletzt gewählten Wert in die Cloud schreiben."""
        self._debounce_unsub = None
        pending = self._pending
        self._pending = None
        if pending is None:
            return
        action, optimistic = pending
        self._optimistic = optimistic
        self._cooldown_until = datetime.now() + CLOUD_COOLDOWN
        self.async_write_ha_state()
        try:
            await action()
        except HagerCloudError as err:
            self._cooldown_until = None
            self.async_write_ha_state()
            _LOGGER.error("Schreiben in die Hager flow Cloud fehlgeschlagen: %s", err)
            await self.coordinator.async_request_refresh()
            return
        await self.coordinator.async_request_refresh()
        # Früh bestätigen: regelmäßig nachsehen, ob das Gerät den Wert übernommen hat
        self._schedule_confirm_poll()
        # Fallback: Maske/Sperre nach Ablauf der Sperre in jedem Fall beenden
        self.async_on_remove(
            async_call_later(self.hass, CLOUD_COOLDOWN.total_seconds() + 1, self._async_cooldown_over)
        )

    def _schedule_confirm_poll(self) -> None:
        if self._confirm_unsub is not None:
            self._confirm_unsub()
        self._confirm_unsub = async_call_later(
            self.hass, CLOUD_CONFIRM_INTERVAL.total_seconds(), self._async_confirm_poll
        )

    async def _async_confirm_poll(self, _now: Any = None) -> None:
        """Erzwingt einen Refresh; die Bestätigung selbst beendet die Maske in
        _handle_coordinator_update. Läuft, bis das Gerät bestätigt hat oder die Sperre endet."""
        self._confirm_unsub = None
        if not self._cooling_down:
            return
        await self.coordinator.async_refresh()
        if self._cooling_down:
            self._schedule_confirm_poll()

    async def async_will_remove_from_hass(self) -> None:
        if self._debounce_unsub is not None:
            self._debounce_unsub()
            self._debounce_unsub = None
        if self._confirm_unsub is not None:
            self._confirm_unsub()
            self._confirm_unsub = None
        await super().async_will_remove_from_hass()

    async def _async_cooldown_over(self, _now: Any) -> None:
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()
