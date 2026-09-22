"""Config flow für die Hager flow Integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv
from pymodbus.client import ModbusTcpClient

from .const import DOMAIN

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


class CannotConnect(HomeAssistantError):
    """Fehler beim Verbindungsaufbau zum Hager flow System."""
