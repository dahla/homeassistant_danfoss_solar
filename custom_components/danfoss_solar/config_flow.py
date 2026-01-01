from homeassistant import config_entries
from typing import Any 
from homeassistant.core import callback
import voluptuous as vol
import logging

from .const import DOMAIN, CONF_DOMAIN, CONF_USERNAME, CONF_PASSWORD, CONF_INTERVAL

_LOGGER = logging.getLogger(__name__)

class DanfossSolarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(title=user_input["name"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("name"): str,
                vol.Required(CONF_DOMAIN, default="solarpanel.local"): str,
                vol.Required(CONF_USERNAME, default=""): str,
                vol.Required(CONF_PASSWORD, default=""): str,
                vol.Required(CONF_INTERVAL, default=60): int,
            })
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_update_reload_and_abort(
                self._get_reconfigure_entry(),
                data_updates=user_input,
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({
                vol.Required("name"): str,
                vol.Required(CONF_DOMAIN, default="solarpanel.local"): str,
                vol.Required(CONF_USERNAME, default=""): str,
                vol.Required(CONF_PASSWORD, default=""): str,
                vol.Required(CONF_INTERVAL, default=60): int,
            }),
        )