from homeassistant import config_entries
from typing import Any 
from homeassistant.core import callback
import voluptuous as vol
import logging

from .const import DOMAIN, CONF_DOMAIN, CONF_USERNAME, CONF_PASSWORD, CONF_INTERVAL

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({
    vol.Required("name"): str,
    vol.Required(CONF_DOMAIN): str,
    vol.Required(CONF_USERNAME): str,
    vol.Required(CONF_PASSWORD): str,
    vol.Required(CONF_INTERVAL, default=60): int,
})

class DanfossSolarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(title=user_input["name"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        entry = self._get_reconfigure_entry()
        
        if user_input is not None:
            # Update the existing entry with new data
            return self.async_update_reload_and_abort(
                entry, 
                data={**entry.data, **user_input}
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(DATA_SCHEMA, entry.data)
        )