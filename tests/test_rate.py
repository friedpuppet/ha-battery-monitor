"""Time left from how fast the percentage falls (no power sensor)."""

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from homeassistant.core import HomeAssistant

from custom_components.battery_monitor.monitor import BatteryMonitor

from .conftest import FLOOR, RUNTIME, SOC, make_entry, setup_entry

BATTERY = SOC


async def start(hass: HomeAssistant, soc: float, floor: float = 0) -> BatteryMonitor:
    hass.states.async_set(BATTERY, str(soc))
    hass.states.async_set(FLOOR, str(floor))
    battery = BatteryMonitor(hass, "e", entity_id=BATTERY, floor_entity=FLOOR)
    await battery.async_load()
    battery.async_start()
    return battery


async def discharge(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, soc: float, to: float, step: float = 1, per_hour: float = 12
) -> float:
    """Walk the sensor from ``soc`` down to ``to``."""
    seconds = step / per_hour * 3600
    while soc > to:
        soc = round(soc - step, 1)
        freezer.tick(timedelta(seconds=seconds))
        hass.states.async_set(BATTERY, str(soc))
        await hass.async_block_till_done()
    return soc


@pytest.mark.parametrize("step", [0.1, 1])
async def test_rate_is_independent_of_the_sensor_step(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, step: float
) -> None:
    battery = await start(hass, 90)
    await discharge(hass, freezer, 90, 80, step=step, per_hour=12)
    assert battery.median_rate == pytest.approx(12, rel=0.02)
    assert battery.runtime_minutes == pytest.approx(400, rel=0.02)
    battery.async_stop()


async def test_needs_three_segments(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    battery = await start(hass, 90)
    await discharge(hass, freezer, 90, 88)
    assert battery.median_rate is None and battery.runtime_minutes is None
    await discharge(hass, freezer, 88, 87)
    assert battery.median_rate == pytest.approx(12)
    battery.async_stop()


async def test_slow_whole_percent_battery_gets_an_estimate(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    battery = await start(hass, 97, floor=20)
    await discharge(hass, freezer, 97, 94, per_hour=4)  # 1 % per 15 min, as the Deye at 600 W
    assert battery.median_rate == pytest.approx(4)
    assert battery.runtime_minutes == pytest.approx((94 - 20) / 4 * 60)
    battery.async_stop()


async def test_follows_a_change_of_load(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    battery = await start(hass, 90)
    soc = await discharge(hass, freezer, 90, 80, per_hour=6)
    await discharge(hass, freezer, soc, soc - 3, per_hour=30)  # 6 minutes later
    assert battery.median_rate == pytest.approx(30)
    battery.async_stop()


async def test_median_ignores_a_burst(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    battery = await start(hass, 90)
    soc = await discharge(hass, freezer, 90, 87)
    soc = await discharge(hass, freezer, soc, soc - 1, per_hour=120)  # a kettle
    await discharge(hass, freezer, soc, soc - 1)
    assert battery.median_rate == pytest.approx(12)
    battery.async_stop()


async def test_old_segments_expire(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    battery = await start(hass, 90)
    await discharge(hass, freezer, 90, 80)
    assert battery.median_rate is not None
    freezer.tick(timedelta(minutes=91))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert battery.median_rate is None
    battery.async_stop()


async def test_idle_stretch_is_not_a_slow_segment(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    battery = await start(hass, 100)
    freezer.tick(timedelta(hours=10))
    await discharge(hass, freezer, 100, 96)
    assert min(rate for _, rate in battery._segments) == pytest.approx(12)
    battery.async_stop()


async def test_floor_shortens_the_runtime(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    battery = await start(hass, 60, floor=15)
    await discharge(hass, freezer, 60, 55)
    assert battery.runtime_minutes == pytest.approx((55 - 15) / 12 * 60)
    hass.states.async_set(BATTERY, "14")
    await hass.async_block_till_done()
    assert battery.runtime_minutes == 0
    hass.states.async_set(FLOOR, "unavailable")  # the inverter out of sight: the last known floor
    hass.states.async_set(BATTERY, "50")
    await hass.async_block_till_done()
    assert battery.floor == 15
    battery.async_stop()


async def test_runtime_sensor(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    hass.states.async_set(BATTERY, "90")
    hass.states.async_set(FLOOR, "0")
    await setup_entry(hass, make_entry(power=False))
    assert hass.states.get(RUNTIME).state == "unknown"
    await discharge(hass, freezer, 90, 84)
    state = hass.states.get(RUNTIME)
    assert state.state == "420"
    assert state.attributes["unit_of_measurement"] == "min"
    assert state.attributes["median_rate"] == 12
    assert "method" not in state.attributes
