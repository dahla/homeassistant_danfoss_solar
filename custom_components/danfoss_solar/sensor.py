import logging
from datetime import timedelta

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
    SensorDeviceClass
)
from homeassistant.const import UnitOfPower, UnitOfEnergy
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed
)
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, CONF_DOMAIN, CONF_USERNAME, CONF_PASSWORD, CONF_INTERVAL
from .api import DanfossSolarAPI  # Import your new API class

_LOGGER = logging.getLogger(__name__)

POWER_ENTRY = "power"
DAILY_PRODUCTION_ENTRY = "daily_production"
TOTAL_PRODUCTION_ENTRY = "total_production"

async def async_setup_entry(hass, entry, async_add_entities):
    config = {**entry.data, **entry.options}
    
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

# Get the HA managed session
    session = async_get_clientsession(hass)

    # Pass the session to the API
    api = DanfossSolarAPI(session)

    # Initialize the Coordinator
    coordinator = DanfossSolarCoordinator(hass, api, config)
        
    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()


    sensors = [
        DanfossSolarInverter(coordinator, entry, config, POWER_ENTRY,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            unit=UnitOfPower.WATT),
        DanfossSolarInverter(coordinator, entry, config, DAILY_PRODUCTION_ENTRY,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            unit=UnitOfEnergy.WATT_HOUR),
        DanfossSolarInverter(coordinator, entry, config, TOTAL_PRODUCTION_ENTRY,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            unit=UnitOfEnergy.WATT_HOUR),
    ]

    async_add_entities(sensors)


class DanfossSolarCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(self, hass, api, config):
        """Initialize."""
        self.api = api
        self.config = config
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=config[CONF_INTERVAL]),
        )

    async def _async_update_data(self):
        """Fetch data from the API file."""
        try:
            # Call the method in api.py with parameters
            return await self.api.get_inverter_data(
                domain=self.config[CONF_DOMAIN],
                username=self.config[CONF_USERNAME],
                password=self.config[CONF_PASSWORD]
            )
        except Exception as err:
            # Raising UpdateFailed notifies HA that the entities are now 'unavailable'
            raise UpdateFailed(f"Error communicating with API: {err}")


class DanfossSolarInverter(CoordinatorEntity, SensorEntity):
    """Representation of a Danfoss Sensor."""

    def __init__(self, coordinator, entry, config, suffix, 
                 device_class, state_class, unit):
        super().__init__(coordinator)
        
        self._suffix = suffix
        self._attr_name = f"{config['name']} {suffix}"
        self._attr_unique_id = f"{entry.entry_id}_{suffix.lower()}"
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_native_unit_of_measurement = unit

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=config["name"],
            manufacturer="Danfoss Solar",
        )

    @property
    def native_value(self):
        """Return the state from the coordinator data."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._suffix)