"""Constants for Battery Monitor."""

from typing import Final

DOMAIN: Final = "battery_monitor"

CONF_SOC_ENTITY: Final = "soc_entity"  # any sensor with a charge in percent
CONF_POWER_ENTITY: Final = "power_entity"  # W or kW, positive while discharging, optional
CONF_CAPACITY: Final = "capacity"  # kWh of the full battery (0–100 %), needed with the power
CONF_FLOOR_ENTITY: Final = "floor_entity"  # % the battery is discharged to, optional

STORAGE_VERSION: Final = 1
