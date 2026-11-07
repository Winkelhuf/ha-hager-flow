"""Die Hager flow Modbus Integration."""
from __future__ import annotations

import logging

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .cloud import CloudTokens, HagerFlowCloudApi, HagerFlowCloudCoordinator
from .const import (
    CONF_CLOUD_ACCESS_TOKEN,
    CONF_CLOUD_EMAIL,
    CONF_CLOUD_ENABLED,
    CONF_CLOUD_INSTALLATION,
    CONF_CLOUD_PASSWORD,
    CONF_CLOUD_REAUTH_TOKEN,
)
from .coordinator import HagerFlowCoordinator
from .data import HagerFlowConfigEntry, HagerFlowData

_LOGGER = logging.getLogger(__name__)

# Hier definieren wir, welche Plattformdateien Home Assistant laden soll
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH, Platform.SELECT]


async def async_setup_entry(hass: HomeAssistant, entry: HagerFlowConfigEntry) -> bool:
    """Wird aufgerufen, wenn die Integration in Home Assistant geladen wird."""
    host = entry.data.get("host")

    # Erstellt deinen funktionierenden Modbus-Coordinator
    coordinator = HagerFlowCoordinator(hass, host)

    # Modbus-Verbindung beim Entladen/Neuladen sauber schließen (sonst bleibt bei jedem
    # Reload eine TCP-Verbindung zum EMC offen)
    async def _async_close_client() -> None:
        await hass.async_add_executor_job(coordinator.client.close)

    entry.async_on_unload(_async_close_client)

    # Erste Gerätesuche und Datenabruf durchführen
    await coordinator.async_config_entry_first_refresh()

    # Optionaler Cloud-Zugang – Modbus bleibt die Hauptquelle. Ein Cloud-Fehler
    # verhindert den Start nicht, nur die Cloud-Entitäten sind dann nicht verfügbar.
    cloud = await _async_setup_cloud(hass, entry)

    # Befüllen von runtime_data mit Client und Coordinator
    entry.runtime_data = HagerFlowData(
        client=None,
        coordinator=coordinator,
        integration=None,
        cloud=cloud,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Optionen geändert (Cloud an/aus, Zugangsdaten) -> neu laden. Der Listener feuert
    # auch, wenn nur neue Tokens in entry.data landen – das darf keinen Reload auslösen.
    options_at_setup = dict(entry.options)

    async def _async_reload_on_options_change(hass: HomeAssistant, updated: HagerFlowConfigEntry) -> None:
        if dict(updated.options) != options_at_setup:
            await hass.config_entries.async_reload(updated.entry_id)

    entry.async_on_unload(entry.add_update_listener(_async_reload_on_options_change))

    return True


async def _async_setup_cloud(hass: HomeAssistant, entry: HagerFlowConfigEntry) -> HagerFlowCloudCoordinator | None:
    """Cloud-Client und -Coordinator anlegen, wenn in den Optionen aktiviert."""
    options = entry.options
    if not options.get(CONF_CLOUD_ENABLED) or not options.get(CONF_CLOUD_INSTALLATION):
        return None

    tokens = None
    if entry.data.get(CONF_CLOUD_ACCESS_TOKEN) and entry.data.get(CONF_CLOUD_REAUTH_TOKEN):
        tokens = CloudTokens(entry.data[CONF_CLOUD_ACCESS_TOKEN], entry.data[CONF_CLOUD_REAUTH_TOKEN])

    def _persist_tokens(new: CloudTokens) -> None:
        # In entry.data (nicht options), damit kein Reload ausgelöst wird
        hass.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                CONF_CLOUD_ACCESS_TOKEN: new.access_token,
                CONF_CLOUD_REAUTH_TOKEN: new.reauth_token,
            },
        )

    api = HagerFlowCloudApi(
        async_get_clientsession(hass),
        options[CONF_CLOUD_EMAIL],
        options[CONF_CLOUD_PASSWORD],
        installation_id=int(options[CONF_CLOUD_INSTALLATION]),
        tokens=tokens,
        on_tokens=_persist_tokens,
    )
    cloud = HagerFlowCloudCoordinator(hass, api)
    await cloud.async_refresh()
    if not cloud.last_update_success:
        _LOGGER.warning(
            "Hager flow Cloud beim Start nicht erreichbar – Modbus läuft normal weiter, "
            "Cloud-Entitäten folgen, sobald die Cloud wieder antwortet"
        )
    return cloud


async def async_unload_entry(hass: HomeAssistant, entry: HagerFlowConfigEntry) -> bool:
    """Wird aufgerufen, wenn die Integration entfernt oder neu geladen wird."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
