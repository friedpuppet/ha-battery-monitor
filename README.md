# Battery Monitor

Home Assistant integration: the state, sessions, time left, time to full and measured capacity of one battery, from
its charge sensor and, optionally, its power sensor. It knows nothing about inverters or phones: everything comes from
the entities picked in its options.

## Options

- **Charge**: any sensor with a charge in percent (required).
- **Power** (optional): battery power in W or kW, positive while discharging.
- **Capacity** (kWh of the full battery, 0–100 %): needed with the power (the flows refuse a power sensor without it).
- **Floor** (optional): an entity with the charge in % the battery is discharged to, e.g. an inverter's shutdown SOC.
  The time left counts down to it; while it has no number the last known one is used, 0 % if there never was one.

## How it works

**Without a power sensor** only the time left is known: charge above the floor divided by the discharge rate. The rate
is the median of the last five segments in which the charge fell by one point, within the last 90 minutes; it needs at
least three of them, so a battery losing less than 2 %/h gets no estimate.

**With a power sensor and a capacity:**

- **State**: the 5-minute time-weighted mean power above 100 W is discharging, below −100 W charging, within ±60 W
  idle, in between the previous state. Two readings in a row beyond ±300 W switch at once (the mean lags a reversal),
  and the state holds while the reading stays beyond ±100 W the same way. An inverter on float charge flickering
  around zero stays idle.
- **Session**: the time the battery stays in one state. It survives a restart.
- **Smoothed power**, per session: per-minute time-weighted means, each through a median of the last 15 minutes (a
  kettle or a dip of a few minutes doesn't count), then a 45-minute exponential average that is the plain mean during
  the first minutes of the session.
- **Time left** (discharging only) = charge above the floor × capacity / smoothed power.
- **Time to full** (charging only) = charge below 100 % × capacity / smoothed power.
- **Measured capacity**: the energy given in a discharge session over its fall of charge, once the charge has fallen
  5 %. It is kept after the session ends, until the next discharge measures again.
- While the power sensor has no reading, the time left falls back to the percentage rate.

## Entities

All on one service device named after the entry.

| Entity | Purpose |
|---|---|
| `sensor.<name>_time_left` | Minutes to the floor; with a power sensor only while discharging. Attributes `floor`, `median_rate` (%/h); with power also `method` (`power`/`soc`), `smoothed_power` (W), `capacity` (kWh). |
| `sensor.<name>_state` | With power. `discharging` / `charging` / `idle`. Attributes `since`, `mean_power` (W, 5-minute mean). |
| `sensor.<name>_session` | With power. Start of the current session. Attributes `state`, `start_soc`, `energy` (kWh moved so far), `previous_state`, `previous_start`, `previous_end`, `previous_energy`. |
| `sensor.<name>_time_to_full` | With power. Minutes to 100 % while charging. Attribute `smoothed_power`. |
| `sensor.<name>_measured_capacity` | With power. kWh of the full battery. Attributes `measuring` (the current discharge is measuring it), `drop` (% the measurement is over), `measured_at`. |

## Development

```sh
uv sync
uv run pytest -q
```
