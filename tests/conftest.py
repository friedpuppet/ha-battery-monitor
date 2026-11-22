"""Fixtures for Battery Monitor tests."""

from __future__ import annotations

from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.battery_monitor.const import (
    CONF_CAPACITY,
    CONF_FLOOR_ENTITY,
    CONF_POWER_ENTITY,
    CONF_SOC_ENTITY,
    DOMAIN,
)

SOC = "sensor.inverter_battery"
POWER = "sensor.inverter_battery_power"
FLOOR = "number.inverter_shutdown_soc"
RUNTIME = "sensor.battery_time_left"
SESSION = "sensor.battery_session"
STATE = "sensor.battery_state"
TO_FULL = "sensor.battery_time_to_full"
CAPACITY = "sensor.battery_measured_capacity"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


def make_entry(power: bool = True, **options: Any) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Battery",
        data={},
        options={
            CONF_SOC_ENTITY: SOC,
            CONF_FLOOR_ENTITY: FLOOR,
            **({CONF_POWER_ENTITY: POWER, CONF_CAPACITY: 16} if power else {}),
            **options,
        },
    )


async def setup_entry(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
