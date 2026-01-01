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

# Keys must match the dictionary keys in api.py exactly
POWER_ENTRY = "power"
DAILY_PRODUCTION_ENTRY = "daily_production"
TOTAL_PRODUCTION_ENTRY = "total_production"

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the sensor platform."""
    
    # Retrieve the coordinator created in __init__.py
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Use entry.data as the source for the base name
    config = entry.data

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


class DanfossSolarInverter(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry, config, suffix, 
                 device_class, state_class, unit):
        super().__init__(coordinator)
        
        self._suffix = suffix
        # Hardcoded mapping for pretty names
        friendly_names = {
            "power": "Current Power",
            "daily_production": "Production Today",
            "total_production": "Lifetime Production"
        }
        _LOGGER.debug("Initialization values - Suffix: %s, Device Class: %s, State Class: %s, Unit: %s",
                      suffix, device_class, state_class, unit)
        base_name = entry.data.get("name", "Danfoss")
        pretty_suffix = friendly_names.get(suffix, suffix.replace("_", " ").title())
        
        # This sets the name you see in the UI
        self._attr_name = f"{base_name} {pretty_suffix}"
        
        # Unique ID stays internal (do not change this or you get duplicate entities)
        self._attr_unique_id = f"{entry.entry_id}_{suffix.lower()}"
        
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_native_unit_of_measurement = unit

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=base_name,
            manufacturer="Danfoss Solar",
            model="Solar Inverter Web Interface"
        )

    @property
    def native_value(self):
        """Return the state from the coordinator data."""
        if self.coordinator.data is None:
            _LOGGER.debug("Sensor %s is waiting for coordinator data", self.name)
            return None
            
        value = self.coordinator.data.get(self._suffix)
        
        if value is None:
            _LOGGER.warning("Key '%s' not found in coordinator data", self._suffix)
            
        return value