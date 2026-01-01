import logging
from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
    SensorDeviceClass
)
from homeassistant.const import UnitOfPower, UnitOfEnergy
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up sensors from a config entry."""
    _LOGGER.debug("Starting sensor setup for Danfoss Solar")
    
    # Get coordinator from hass.data (setup in __init__.py)
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Map the internal API keys to pretty display names
    # You can change the strings on the right to whatever you prefer
    sensors_to_create = [
        ("power", "Current power", SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT),
        ("daily_production", "Daily production", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.WATT_HOUR),
        ("total_production", "Total production", SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, UnitOfEnergy.WATT_HOUR),
    ]

    entities = []
    for key, friendly_name, device_class, state_class, unit in sensors_to_create:
        entities.append(
            DanfossSolarInverter(coordinator, entry, key, friendly_name, device_class, state_class, unit)
        )

    async_add_entities(entities)

class DanfossSolarInverter(CoordinatorEntity, SensorEntity):
    """Representation of a Danfoss Sensor."""

    def __init__(self, coordinator, entry, key, friendly_name, device_class, state_class, unit):
        super().__init__(coordinator)
        self._key = key
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_native_unit_of_measurement = unit

        # Naming Logic
        # This will show up as e.g. "Dahls solceller Solar Power"
        base_name = entry.data.get("name", "Danfoss")
        self._attr_name = f"{base_name} {friendly_name}"
        
        # Unique ID is critical - do not change this if you want to keep history
        self._attr_unique_id = f"{entry.entry_id}_{key}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=base_name,
            manufacturer="Danfoss Solar",
        )

    @property
    def native_value(self):
        """Return the state from coordinator data."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._key)