"""Sensors: state, session, time left, time to full and measured capacity of the battery."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import UnitOfEnergy, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import BatteryMonitorConfigEntry
from .const import DOMAIN
from .monitor import BATTERY_STATES, CHARGING, DISCHARGING, BatteryMonitor


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BatteryMonitorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    monitor = entry.runtime_data
    entities: list[SensorEntity] = [RuntimeSensor(entry, monitor)]
    if monitor.uses_power:
        entities += [
            StateSensor(entry, monitor),
            SessionSensor(entry, monitor),
            TimeToFullSensor(entry, monitor),
            MeasuredCapacitySensor(entry, monitor),
        ]
    async_add_entities(entities)


def _round(value: float | None, digits: int = 0) -> float | int | None:
    if value is None:
        return None
    return round(value, digits) if digits else round(value)


class _MonitorEntity(SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, entry: BatteryMonitorConfigEntry, monitor: BatteryMonitor, key: str) -> None:
        self._monitor = monitor
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self._monitor.async_add_listener(self._on_change))

    @callback
    def _on_change(self) -> None:
        self.async_write_ha_state()


class RuntimeSensor(_MonitorEntity):
    """Time left to the floor; with a power sensor only while discharging."""

    _attr_icon = "mdi:battery-clock-outline"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES

    def __init__(self, entry: BatteryMonitorConfigEntry, monitor: BatteryMonitor) -> None:
        super().__init__(entry, monitor, "runtime")

    @property
    def native_value(self) -> int | None:
        return _round(self._monitor.runtime_minutes)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        monitor = self._monitor
        attrs: dict[str, Any] = {"floor": monitor.floor, "median_rate": _round(monitor.median_rate, 1)}
        if monitor.uses_power:
            power = monitor.smoothed_power if monitor.state == DISCHARGING else None
            attrs |= {"method": monitor.method, "smoothed_power": _round(power), "capacity": monitor.capacity}
        return attrs


class TimeToFullSensor(_MonitorEntity):
    """Time to 100 % while charging, at the smoothed power."""

    _attr_icon = "mdi:battery-charging-high"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES

    def __init__(self, entry: BatteryMonitorConfigEntry, monitor: BatteryMonitor) -> None:
        super().__init__(entry, monitor, "time_to_full")

    @property
    def native_value(self) -> int | None:
        return _round(self._monitor.time_to_full_minutes)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        power = self._monitor.smoothed_power if self._monitor.state == CHARGING else None
        return {"smoothed_power": _round(power)}


class StateSensor(_MonitorEntity):
    """Discharging, charging or idle, from the power with hysteresis."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(BATTERY_STATES)

    def __init__(self, entry: BatteryMonitorConfigEntry, monitor: BatteryMonitor) -> None:
        super().__init__(entry, monitor, "state")

    @property
    def native_value(self) -> str | None:
        return self._monitor.state

    @property
    def icon(self) -> str:
        return {
            "discharging": "mdi:battery-arrow-down",
            "charging": "mdi:battery-charging",
            "idle": "mdi:battery-outline",
        }.get(self._monitor.state or "", "mdi:battery-unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        start = self._monitor.session_start
        return {"since": start.isoformat() if start else None, "mean_power": _round(self._monitor.mean_power)}


class SessionSensor(_MonitorEntity):
    """Start of the current session: the time the battery has been in its present state."""

    _attr_icon = "mdi:timer-play-outline"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, entry: BatteryMonitorConfigEntry, monitor: BatteryMonitor) -> None:
        super().__init__(entry, monitor, "session")

    @property
    def native_value(self) -> datetime | None:
        return self._monitor.session_start

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        monitor = self._monitor
        return {
            "state": monitor.state,
            "start_soc": monitor.session_soc,
            "energy": round(monitor.session_energy / 1000, 2) if monitor.session_start else None,
            "previous_state": monitor.previous.get("state"),
            "previous_start": monitor.previous.get("start"),
            "previous_end": monitor.previous.get("end"),
            "previous_energy": monitor.previous.get("energy"),
        }


class MeasuredCapacitySensor(_MonitorEntity):
    """kWh of the full battery: measured in the current discharge once the charge has fallen 5 %, else the last one."""

    _attr_icon = "mdi:battery-heart-variant"
    _attr_device_class = SensorDeviceClass.ENERGY_STORAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 1

    def __init__(self, entry: BatteryMonitorConfigEntry, monitor: BatteryMonitor) -> None:
        super().__init__(entry, monitor, "measured_capacity")

    @property
    def native_value(self) -> float | None:
        if (measured := self._monitor.measured_capacity) is not None:
            return _round(measured, 2)
        return self._monitor.last_capacity.get("kwh")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        monitor = self._monitor
        if monitor.measured_capacity is not None:
            return {"measuring": True, "drop": _round(monitor.capacity_drop, 1), "measured_at": None}
        last = monitor.last_capacity
        return {"measuring": False, "drop": _round(last.get("drop"), 1), "measured_at": last.get("end")}
