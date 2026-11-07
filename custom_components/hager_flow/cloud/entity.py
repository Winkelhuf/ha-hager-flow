"""Basis-Entität für Cloud-Funktionen.

Cloud-Entitäten hängen sich an die bestehenden Modbus-Geräte (EMC bzw. Wallbox),
damit Lesen (Modbus) und Schreiben (Cloud) im selben Gerät erscheinen.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
import logging

from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import DOMAIN
from .api import CloudWallbox
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
    """Gemeinsame Logik: Name aus translations, Kategorie Konfiguration, Fehlerbehandlung."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: HagerFlowCloudCoordinator, entry_id: str, key: str, device_info: DeviceInfo) -> None:
        super().__init__(coordinator)
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry_id}_cloud_{key}"
        self._attr_device_info = device_info

    async def _async_write(self, action: Callable[[], Awaitable[None]]) -> None:
        """Schreibbefehl ausführen, Fehler übersetzt melden und Daten neu laden."""
        try:
            await action()
        except HagerCloudError as err:
            _LOGGER.error("Schreiben in die Hager flow Cloud fehlgeschlagen: %s", err)
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="cloud_write_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        finally:
            await self.coordinator.async_request_refresh()
