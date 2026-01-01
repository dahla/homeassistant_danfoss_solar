"""The Danfoss Solar Inverter integration."""
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DanfossSolarAPI
from .const import (
    DOMAIN, 
    CONF_DOMAIN, 
    CONF_USERNAME, 
    CONF_PASSWORD, 
    CONF_INTERVAL
)

_LOGGER = logging.getLogger(__package__)

# List the platforms to be set up (currently just sensor)
PLATFORMS: list[Platform] = [Platform.SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Danfoss Solar from a config entry."""
    
    # 1. Initialize the API logic
    # We use the built-in HA session for efficiency
    session = async_get_clientsession(hass)
    api = DanfossSolarAPI(session)

    # 2. Setup the Data Coordinator
    # This class handles the update interval and calls your API
    coordinator = DanfossSolarCoordinator(hass, api, entry)

    # 3. Trigger the first data fetch
    # This ensures entities have data immediately when they are created.
    # If the login fails here, the integration setup will fail and show an error.
    await coordinator.async_config_entry_first_refresh()

    # 4. Store the coordinator in hass.data
    # This allows sensor.py to access the shared data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # 5. Setup the platforms (sensor.py)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # 6. Listen for changes in options (like interval changes)
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms (sensor.py)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    # Clean up stored data
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update (e.g., when user changes interval)."""
    await hass.config_entries.async_reload(entry.entry_id)


class DanfossSolarCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Danfoss Solar Inverter."""

    def __init__(self, hass: HomeAssistant, api: DanfossSolarAPI, entry: ConfigEntry) -> None:
        """Initialize."""
        self.api = api
        self.entry = entry
        
        # Pull the interval from the config entry (default to 60s if missing)
        interval = entry.data.get(CONF_INTERVAL, 60)
        
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=int(interval)),
        )

    async def _async_update_data(self):
        """Fetch data from the API."""
        try:
            # We pull the credentials directly from the entry
            data = await self.api.get_inverter_data(
                domain=self.entry.data[CONF_DOMAIN],
                username=self.entry.data[CONF_USERNAME],
                password=self.entry.data[CONF_PASSWORD]
            )
            
            if not data:
                raise UpdateFailed("API returned empty data or login failed")
                
            return data
            
        except Exception as err:
            # Raising UpdateFailed signals HA that the entities are now unavailable
            _LOGGER.exception("Error communicating with Danfoss Inverter")
            raise UpdateFailed(f"Error communicating with API: {err}") from err