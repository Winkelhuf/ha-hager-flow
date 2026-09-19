"""Config flow für die Hager flow Integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv

class HagerFlowConfigFlow(config_entries.ConfigFlow, domain="hager_flow"):
    """Handhabung des Config Flows für Hager flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Erster Schritt bei der manuellen Einrichtung."""
        errors = {}

        if user_input is not None:
            return self.async_create_entry(
                title=f"Hager flow ({user_input['host']})", 
                data=user_input
            )

        DATA_SCHEMA = vol.Schema(
            {
                vol.Required("host", default="192.168.70.30"): cv.string,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )
