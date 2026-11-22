"""Battery Monitor: state, sessions, time left and time to full of a battery."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_CAPACITY, CONF_FLOOR_ENTITY, CONF_POWER_ENTITY, CONF_SOC_ENTITY
from .monitor import BatteryMonitor

PLATFORMS = [Platform.SENSOR]

type BatteryMonitorConfigEntry = ConfigEntry[BatteryMonitor]


async def async_setup_entry(hass: HomeAssistant, entry: BatteryMonitorConfigEntry) -> bool:
    opts = entry.options
    monitor = BatteryMonitor(
        hass,
        entry.entry_id,
        entity_id=opts[CONF_SOC_ENTITY],
        floor_entity=opts.get(CONF_FLOOR_ENTITY) or None,
        power_entity=opts.get(CONF_POWER_ENTITY) or None,
        capacity=opts.get(CONF_CAPACITY) or None,
    )
    await monitor.async_load()
    entry.runtime_data = monitor
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    monitor.async_start()
    entry.async_on_unload(monitor.async_stop)
    entry.async_on_unload(entry.add_update_listener(_async_entry_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BatteryMonitorConfigEntry) -> bool:
    await entry.runtime_data.async_flush()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_entry_updated(hass: HomeAssistant, entry: BatteryMonitorConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
