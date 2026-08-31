# Data / Данные

Three kinds of file live here, and they are kept apart on purpose.

Здесь три типа файлов, и они намеренно разделены.

| Kind | Where | What it means |
|---|---|---|
| **Templates** | `*_TEMPLATE.csv` | Empty tables with the column schema and the measurement conditions fixed **before** the experiment. |
| **Simulation output** | `results/*_sim.csv`, `simulation_summary.json` | Produced by `analysis/simulate_controllers.py`. Computed, never measured. |
| **Bench measurements** | `calibration/run_*.csv`, `results/run_*.csv` | Recorded from the rig. **None exist yet** — the sensor bracket is not built. |

## Why the templates come first

The column schema, the number of repeats and the acceptance thresholds are
written down before any measurement is taken, and the `predicted` column is
filled from the simulation before the rig runs. If the bench then disagrees
with the model, the disagreement is visible in the same table instead of
disappearing into a quietly re-tuned parameter.

Схема таблицы, число повторов и пороги приёмки фиксируются до измерений, а
колонка `predicted` заполняется из симуляции до запуска стенда. Если стенд
разойдётся с моделью, расхождение будет видно в той же таблице, а не исчезнет
в тихо подстроенном параметре.

## Current status

- `calibration/` — empty. Blocked on the sensor bracket (build step 3).
- `results/controller_comparison_TEMPLATE.csv` — `predicted` filled, `measured` empty.
- `results/controller_comparison_sim.csv` — full simulation results, available now.
