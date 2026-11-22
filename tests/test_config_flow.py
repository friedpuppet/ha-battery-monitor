"""Config and options flow."""

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.battery_monitor.const import (
    CONF_CAPACITY,
    CONF_FLOOR_ENTITY,
    CONF_POWER_ENTITY,
    CONF_SOC_ENTITY,
    DOMAIN,
)

from .conftest import FLOOR, POWER, SOC, make_entry, setup_entry


async def test_user_flow(hass: HomeAssistant) -> None:
    hass.states.async_set(SOC, "80", {"device_class": "battery"})
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Батарея", CONF_SOC_ENTITY: SOC, CONF_POWER_ENTITY: POWER, CONF_CAPACITY: 15}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Батарея"
    assert result["options"] == {CONF_SOC_ENTITY: SOC, CONF_POWER_ENTITY: POWER, CONF_CAPACITY: 15}
    await hass.async_block_till_done()

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "x", CONF_SOC_ENTITY: SOC})
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "already_configured"


async def test_options_flow_reloads(hass: HomeAssistant) -> None:
    hass.states.async_set(SOC, "80")
    hass.states.async_set(FLOOR, "15")
    entry = make_entry(power=False)
    await setup_entry(hass, entry)
    assert not entry.runtime_data.uses_power
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_SOC_ENTITY: SOC, CONF_POWER_ENTITY: POWER, CONF_CAPACITY: 15, CONF_FLOOR_ENTITY: FLOOR},
    )
    await hass.async_block_till_done()
    assert entry.runtime_data.uses_power
    assert entry.runtime_data.floor == 15
