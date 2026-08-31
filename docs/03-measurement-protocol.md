# 03 — Measurement protocol

*[Русская версия](03-measurement-protocol.ru.md)*

---

## Why this document exists before the data

Every threshold, repeat count and acceptance criterion below was fixed while
the rig was still being built, and the `predicted` column of every table was
filled from `analysis/simulate_controllers.py` before the bench could produce
a single number.

This ordering is deliberate. On a plant this sensitive it is trivially easy to
adjust a filter constant, re-tune a gain, and end up reporting whichever
configuration happened to look best — without ever noticing that the model was
being fitted to the outcome rather than tested by it. Writing the protocol
first turns a disagreement between prediction and measurement into a visible
result instead of an invisible correction.

Where a prediction later proves wrong, **the prediction stays in the table.**

---

## P1 — Coil characterisation

**Blocked by:** nothing. Can be run today.

| Step | Action |
|---|---|
| 1 | Measure winding resistance cold, four-wire if available |
| 2 | Compute $i = U/R$ and compare with the 0.44 A design assumption |
| 3 | Apply 12 V for 10 min, logging case temperature every minute |
| 4 | Re-measure resistance hot, immediately after power-off |

| Quantity | Predicted | Measured | Unit |
|---|---|---|---|
| $R_{cold}$ | 27 (assumed) | — | Ω |
| $R_{hot}$ after 10 min | 30–32 (Cu tempco 0.39 %/K) | — | Ω |
| $i$ at 12 V, cold | 0.44 | — | A |
| Case temperature rise | — | — | K |

**Acceptance:** all four cells filled. **Why it matters:** $R$ sets the bias
duty (0.5625 by design); a 15 % drift in $R$ moves the equilibrium operating
point and is the leading candidate explanation if the ball drifts downward
over minutes.

## P2 — Coil inductance and the current observer

**Blocked by:** P1. **Instrument:** INA219 + oscilloscope on the drain.

Drive a duty staircase (`firmware/03_ina219_test`), record settled current at
each step, then measure the current rise time on a step from 0 to 50 % duty.

| Quantity | Predicted | Measured | Unit |
|---|---|---|---|
| $L$ | 40 (assumed, pot-core class) | — | mH |
| $\tau_e = L/R$ | 1.48 | — | ms |
| Linearity of $i$ vs duty, $R^2$ | > 0.99 | — | — |

**Acceptance:** $\tau_e$ known to ±20 %. **Why it matters:** `firmware/05`
estimates coil current from duty through a first-order observer with this
exact constant, because the INA219 needs 0.5 ms per reading and cannot run
inside a 1 ms loop. If $\tau_e$ is wrong, the third network input is wrong.

## P3 — Position sensor calibration ⭐

**Blocked by:** the sensor bracket. **This is the gating experiment for the
entire project** — without a position signal the loop cannot be closed.

Schema and empty table: [`data/calibration/hall_calibration_TEMPLATE.csv`](../data/calibration/hall_calibration_TEMPLATE.csv)

Two sweeps, because the differential pair has two jobs and both must be
verified:

**Sweep A — the calibration curve.** Ball held at a known gap with a
non-magnetic gauge, coil at minimum duty. Gap from 1.0 to 4.0 mm in 0.5 mm
steps, 25 repeats per point.

| Gap, mm | diff (predicted trend) | diff measured | SD, counts |
|---|---|---|---|
| 1.0 | largest | — | — |
| 1.5 | ↓ monotone | — | — |
| 2.0 | ↓ | — | — |
| **2.5** | **operating point** | — | — |
| 3.0 | ↓ | — | — |
| 3.5 | ↓ | — | — |
| 4.0 | smallest | — | — |

**Sweep B — common-mode rejection.** *No ball present.* Duty stepped 0 → 512 →
1024 → 1536 at each sensor position. Ideally `diff` does not move at all; the
residual slope is the leakage of coil current into the position signal.

| Quantity | Target | Measured |
|---|---|---|
| Monotonicity of diff(gap) over 1–4 mm | strictly monotone | — |
| Sensitivity at $x_0$ | maximised by sensor placement | — |
| Common-mode leakage $\partial(\text{diff})/\partial(\text{duty})$ | as close to 0 as placement allows | — |
| Apparent motion over full duty range | < 100 µm equivalent | — |
| Noise SD after 16× oversampling | < 4 µm equivalent | — |

**Acceptance:** monotone curve, quadratic fit residual below 20 µm RMS,
apparent motion from current below 100 µm equivalent.

**If acceptance fails:** this is the project's main technical risk, and two
fallbacks are pre-committed rather than improvised — see
[`05-limitations.md`](05-limitations.md#risk-1).

Processing: `python3 analysis/fit_calibration.py` → the polynomial
coefficients pasted into `CAL_C0..CAL_C2` in the firmware.

## P4 — Plant identification

**Blocked by:** P3. Step the duty around the operating point in both
directions and record the position response; fit $k$ in $F = k(i/x)^2$.

| Quantity | Predicted | Measured |
|---|---|---|
| Force constant $k$ | 4.01 µN·m²/A² (by construction) | — |
| Unstable pole from the fit | 88.6 rad/s | — |
| Divergence τ | 11.3 ms | — |

**Acceptance:** identified pole within ±30 % of prediction. A larger
disagreement is a result in its own right and is reported as such — the most
likely cause would be that the real force law departs from the inverse-square
form at a 2.5 mm gap on a pot-core magnet, which is exactly the regime
[`01`](01-actuator-analysis.md) argues is non-standard.

## P5 — Controller comparison ⭐

**Blocked by:** P3, P4 and a working PID. This is the measurement the project
exists for.

Table: [`data/results/controller_comparison_TEMPLATE.csv`](../data/results/controller_comparison_TEMPLATE.csv)

Identical conditions for all four controllers — same setpoint, same
disturbance, same session, alternating order to cancel thermal drift:

| Metric | Definition | Predicted (PID / MPC / f32 / int8) |
|---|---|---|
| RMS hold error | SD of gap over a 60 s steady-state window | 2.36 / 2.61 / 2.68 / 3.55 µm |
| Settling time | to ±50 µm after a calibrated impulse | 33.1 / 17.8 / 18.0 / 17.6 ms |
| Capture range | largest initial offset that still recovers | 1.78 / 1.78 / 1.77 / 1.32 mm |
| Step time | GPIO 17 pulse width on the scope | — / — / — / — µs |
| Footprint | bytes of weights | — / — / 1412 / 452 B |

**Disturbance.** A light pendulum released from a fixed height, not a finger
flick: the impulse must be reproducible, and a finger is not.

**Repeats.** 10 runs per controller per metric, reported as mean ± SD.
Simulation SDs above come from 8 noise realisations.

**Acceptance:** all four rows complete with SDs. The headline figure is the
float32 and int8 step responses overlaid.

**The prediction to test.** Simulation says int8 costs 1.33× in hold precision,
nothing in settling time, and 25 % of the capture range. The capture-range loss
is the least obvious of the three and the one most likely to be modified by
real noise and heating. **If the bench contradicts it, the bench wins and the
contradiction is the paper.**

## P6 — Robustness

**Blocked by:** P5. Repeat P5 with Ø8 and Ø12 mm spheres, controller
unchanged. Mass changes by ±50 % and ∓70 %; the equilibrium current and the
pole both move. Reported as the degradation of each P5 metric.

---

## Instrumentation and its limits

| Instrument | Used for | Known limitation |
|---|---|---|
| Oscilloscope | drain waveform, step time via GPIO 17 | the only direct step-time measurement available |
| INA219 | coil current, P1, P2 | 0.5 ms per reading — outside the loop only |
| Multimeter | resistance, divider voltages | 4-wire not available: expect ±0.3 Ω on $R_{cold}$ |
| Feeler gauge | gap setting in P3 | ±0.05 mm, i.e. 2 % of the working gap — this propagates into every calibration point |
| Wi-Fi telemetry | 1 kHz logging to a browser | must never be inside the control task |

The gauge tolerance is the dominant systematic error of P3 and therefore the
floor under every position figure in P5. It is stated here rather than
discovered later.
