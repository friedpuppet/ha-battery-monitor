# battery-monitor — Home Assistant integration

Subproject of `homeassistant` (see `../AGENTS.md`). Custom integration **`battery_monitor`**: battery state, sessions,
time left, time to full and measured capacity from a charge sensor and, optionally, a power sensor. Step 1 of the
split in `../battery-split-plan.md` (2026-11-22, the user's option A): the analysis moved here from
`grid_load_shedding`'s `battery.py` (v0.11.0); the sound levels (`passed`, re-arm, crossings) did not, they go to
`../power-sounds/`. README has the logic and the entities.

## Status

- **v0.1.0 released and live 2026-11-22.** Repo **[friedpuppet/ha-battery-monitor](https://github.com/friedpuppet/ha-battery-monitor)**
  (public, created by the user), `origin` without credentials. Push with the PAT `~/.config/github/token-grid-load-shedding`
  (the user added this repo to it): `git -c http.https://github.com/.extraheader="AUTHORIZATION: basic $(printf 'x-access-token:%s' "$(cat ~/.config/github/token-grid-load-shedding)" | base64 -w0)" push`.
  Releases via the GitHub API with the same PAT.
- Marketplace custom repository, repo id **`1467925568`** (added with WS `marketplace/repositories/add`,
  `repository: "friedpuppet/ha-battery-monitor"`, `category: "integration"`). Update: bump version, push, release,
  WS `marketplace/repository/install` `repository: "1467925568"`, `version: "vX.Y.Z"`, restart Core. The first
  install needed no restart.
- Live entry **«Монітор батареї»** `01M82D23HPDCS81QC02YWR3DVZ`: charge `sensor.vkhidna_zona_deye_inverter_battery`,
  power `…_battery_power`, 15 kWh, floor `number.vkhidna_zona_deye_inverter_battery_shutdown_soc`. Entities
  `sensor.monitor_batarei_time_left` / `_state` / `_session` / `_time_to_full` / `_measured_capacity`. Runs alongside
  grid_load_shedding's own `sensor.merezha_battery_*` (removed in its v0.12.0 the same evening) to compare (first minutes: 520 vs 449 min, its 45-min
  average had just started; an hour later 492 vs 457). The dashboard «Інвертор» uses these since 2026-11-22 (plan step 3).
- Same conventions as `../grid-load-shedding/`: personal project, Marketplace custom repository, hassfest + pytest CI,
  bump `manifest.json` `version` per release. The brand icon is a copy of grid_load_shedding's for now.

## Rules (the user's, 2026-11-22)

- Nothing here knows about Deye or about the grid: only the entities picked in the options.
- State and sessions follow the battery's own state (from power), never the grid.
- Time left and time to full come from the power (it updates far more often than the SOC); the percentage is only the
  fallback without a power reading.
- The floor comes from an entity (the inverter's shutdown SOC = the full discharge), not a configured number, and
  doesn't depend on the battery mode.

## Layout

| Path | What |
|---|---|
| `custom_components/battery_monitor/monitor.py` | `BatteryMonitor` (state machine, sessions, `PowerSmoother`, rate segments, persisted in `Store` `battery_monitor.<entry_id>`). No entities, unit-testable. |
| `.../sensor.py` | The five sensors on the entry's service device. |
| `.../config_flow.py` | User flow (name + options), options flow (reloads the entry). |
| `tests/test_power.py` | State, hysteresis, sessions, smoothing, time left / to full, capacity, reload, fallback. |
| `tests/test_rate.py` | The percentage rate without power. |
