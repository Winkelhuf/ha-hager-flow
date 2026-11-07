"""Config flow für die Hager flow Integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from pymodbus.client import ModbusTcpClient

from .cloud import CloudTokens, HagerCloudAuthError, HagerCloudError, HagerFlowCloudApi
from .const import (
    CONF_CLOUD_ACCESS_TOKEN,
    CONF_CLOUD_EMAIL,
    CONF_CLOUD_ENABLED,
    CONF_CLOUD_INSTALLATION,
    CONF_CLOUD_PASSWORD,
    CONF_CLOUD_REAUTH_TOKEN,
    DOMAIN,
)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required("host", default="192.168.70.30"): cv.string,
    }
)


class HagerFlowConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handhabung des Config Flows für Hager flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Erster Schritt bei der manuellen Einrichtung."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input["host"]

            # Verhindert, dass dieselbe IP zweimal eingerichtet wird
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            try:
                await self.hass.async_add_executor_job(self._test_connection, host)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=f"Hager flow ({host})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    @staticmethod
    def _test_connection(host: str) -> None:
        """Prüft, ob unter der IP ein Modbus-TCP-Gerät antwortet (blockierend, läuft im Executor)."""
        client = ModbusTcpClient(host=host, port=502)
        try:
            if not client.connect():
                raise CannotConnect
        finally:
            client.close()


    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> HagerFlowOptionsFlow:
        """Optionen: optionaler Cloud-Zugang."""
        return HagerFlowOptionsFlow()


class HagerFlowOptionsFlow(config_entries.OptionsFlow):
    """Aktiviert den optionalen Cloud-Zugang für per Modbus nicht beschreibbare Funktionen."""

    def __init__(self) -> None:
        self._input: dict[str, Any] = {}
        self._installations: dict[str, str] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        current = self.config_entry.options

        if user_input is not None:
            if not user_input.get(CONF_CLOUD_ENABLED):
                return self.async_create_entry(data={**current, CONF_CLOUD_ENABLED: False})

            self._input = user_input
            api = HagerFlowCloudApi(
                async_get_clientsession(self.hass),
                user_input[CONF_CLOUD_EMAIL],
                user_input[CONF_CLOUD_PASSWORD],
                on_tokens=self._store_tokens,
            )
            try:
                await api.async_login()
                installations = await api.async_get_installations()
                chosen = await self._async_match_installation(api, installations)
            except HagerCloudAuthError:
                errors["base"] = "invalid_auth"
            except HagerCloudError:
                errors["base"] = "cloud_cannot_connect"
            else:
                if not installations:
                    errors["base"] = "no_installations"
                elif chosen is not None:
                    return self._finish(chosen)
                else:
                    self._installations = {
                        str(inst["id"]): _installation_label(inst) for inst in installations if inst.get("id")
                    }
                    return await self.async_step_installation()

        schema = vol.Schema(
            {
                vol.Required(CONF_CLOUD_ENABLED, default=current.get(CONF_CLOUD_ENABLED, False)): bool,
                vol.Optional(CONF_CLOUD_EMAIL, default=current.get(CONF_CLOUD_EMAIL, "")): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.EMAIL, autocomplete="username")
                ),
                vol.Optional(CONF_CLOUD_PASSWORD, default=current.get(CONF_CLOUD_PASSWORD, "")): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD, autocomplete="current-password")
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)

    async def async_step_installation(self, user_input: dict[str, Any] | None = None):
        """Mehrere Anlagen im Konto und keine eindeutig per Seriennummer erkannt -> auswählen."""
        if user_input is not None:
            return self._finish(int(user_input[CONF_CLOUD_INSTALLATION]))
        schema = vol.Schema(
            {
                vol.Required(CONF_CLOUD_INSTALLATION): SelectSelector(
                    SelectSelectorConfig(
                        options=[SelectOptionDict(value=k, label=v) for k, v in self._installations.items()],
                        mode=SelectSelectorMode.LIST,
                    )
                )
            }
        )
        return self.async_show_form(step_id="installation", data_schema=schema)

    def _finish(self, installation_id: int):
        return self.async_create_entry(
            data={
                CONF_CLOUD_ENABLED: True,
                CONF_CLOUD_EMAIL: self._input[CONF_CLOUD_EMAIL],
                CONF_CLOUD_PASSWORD: self._input[CONF_CLOUD_PASSWORD],
                CONF_CLOUD_INSTALLATION: installation_id,
            }
        )

    @callback
    def _store_tokens(self, tokens: CloudTokens) -> None:
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data={
                **self.config_entry.data,
                CONF_CLOUD_ACCESS_TOKEN: tokens.access_token,
                CONF_CLOUD_REAUTH_TOKEN: tokens.reauth_token,
            },
        )

    async def _async_match_installation(self, api: HagerFlowCloudApi, installations: list[dict]) -> int | None:
        """Anlage automatisch über die per Modbus gelesene EMC-Seriennummer finden."""
        ids = [int(inst["id"]) for inst in installations if inst.get("id")]
        if len(ids) == 1:
            return ids[0]
        runtime = getattr(self.config_entry, "runtime_data", None)
        serial = runtime.coordinator.data.get("emc_seriennummer") if runtime and runtime.coordinator.data else None
        if not serial:
            return None
        for inst_id in ids:
            link = await api.async_get_emc_link(inst_id)
            if link and str(link.get("deviceId")).strip() == str(serial).strip():
                return inst_id
        return None


def _installation_label(inst: dict[str, Any]) -> str:
    name = inst.get("name") or inst.get("installationName") or inst.get("description") or ""
    return f"{inst['id']} – {name}" if name else str(inst["id"])


class CannotConnect(HomeAssistantError):
    """Fehler beim Verbindungsaufbau zum Hager flow System."""
