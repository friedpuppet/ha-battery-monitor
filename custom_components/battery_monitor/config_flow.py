"""Config and options flow for Battery Monitor."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import CONF_CAPACITY, CONF_FLOOR_ENTITY, CONF_POWER_ENTITY, CONF_SOC_ENTITY, DOMAIN


def _suggested(defaults: dict[str, Any], key: str) -> dict | None:
    return {"suggested_value": defaults[key]} if defaults.get(key) else None


def _errors(user_input: dict[str, Any]) -> dict[str, str]:
    """The power is used only together with the capacity: without one the power sensors would silently not appear."""
    return {"base": "capacity_missing"} if user_input.get(CONF_POWER_ENTITY) and not user_input.get(CONF_CAPACITY) else {}


def _options_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_SOC_ENTITY, default=defaults.get(CONF_SOC_ENTITY, vol.UNDEFINED)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class=SensorDeviceClass.BATTERY)
            ),
            vol.Optional(CONF_POWER_ENTITY, description=_suggested(defaults, CONF_POWER_ENTITY)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class=SensorDeviceClass.POWER)
            ),
            vol.Optional(CONF_CAPACITY, description=_suggested(defaults, CONF_CAPACITY)): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.1, max=1000, step=0.1, unit_of_measurement="kWh", mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Optional(CONF_FLOOR_ENTITY, description=_suggested(defaults, CONF_FLOOR_ENTITY)): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["number", "sensor"])
            ),
        }
    )


class BatteryMonitorConfigFlow(ConfigFlow, domain=DOMAIN):
    """One entry per battery."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._async_abort_entries_match({CONF_SOC_ENTITY: user_input[CONF_SOC_ENTITY]})
            if not (errors := _errors(user_input)):
                name = user_input.pop(CONF_NAME)
                return self.async_create_entry(title=name, data={}, options=user_input)
        defaults = user_input or {}
        schema = vol.Schema(
            {vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "Battery")): selector.TextSelector()}
        ).extend(_options_schema(defaults).schema)
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return BatteryMonitorOptionsFlow()


class BatteryMonitorOptionsFlow(OptionsFlow):
    """Change the entities and the capacity (the entry reloads afterwards)."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None and not (errors := _errors(user_input)):
            return self.async_create_entry(data=user_input)
        defaults = user_input if user_input is not None else dict(self.config_entry.options)
        return self.async_show_form(step_id="init", data_schema=_options_schema(defaults), errors=errors)
