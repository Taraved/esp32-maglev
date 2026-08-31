# 05 — Limitations and risks

*[Русская версия](05-limitations.ru.md)*

---

## A. Assumptions carried into every number

| Assumption | Value used | How it propagates | Resolved by |
|---|---|---|---|
| Coil resistance | 27 Ω (datasheet class) | sets bias duty 0.5625 and $i_{max}$ | P1, today |
| Coil inductance | 40 mH (pot-core class) | sets $\tau_e$ = 1.48 ms and therefore the current observer in `firmware/05` | P2 |
| Position noise | σ = 4 µm, 2 µm quantisation | **sets every RMS figure and both controller tunings** | P3 |
| Force constant $k$ | 4.01 µN·m²/A², fixed by construction at $(i_0, x_0)$ | sets the pole and the linearised model | P4 |
| Bias current | 0.25 A, chosen at ≈55 % of $i_{max}$ | sets symmetric control authority | P4 |

The third row is the load-bearing one. The PID gains (Kp = 400, Kd = 4) were
selected by a grid search **with the noise model enabled**; without noise the
same search returns Kp = 1600, Kd = 12, which looks superb on a clean signal
and produces 134 µm of jitter once realistic ADC noise is present — a 57×
difference in the reported RMS. **If the real sensor noise differs
substantially from 4 µm, both controllers must be re-tuned and every RMS
number in the comparison table moves.**

## B. Risks

### Risk 1 — the differential Hall pair may not resolve position at 2.5 mm

**Severity: project-critical. Likelihood: high.**

The differential scheme relies on the coil field acting equally on both
sensors while the ball breaks the balance. Two things work against it on this
actuator: the pot-core geometry leaves very little field outside the magnet to
be perturbed in the first place (§01), and the coil's own field at the sensor
positions is orders of magnitude larger than the ball's contribution.

Pre-committed fallbacks, in order:

1. **Pole extender** (option B of §01): an M4 steel bolt in the face pushes
   the field 6–8 mm into the air, giving the sensors something to measure and
   relaxing the pole to ~50 rad/s. Cost: one bolt. Consequence: the actuator is
   no longer the stock part, and the analysis of §01 must be redone for the
   modified geometry.
2. **Optical sensing**: an IR LED and phototransistor across the gap, with the
   ball interrupting the beam. Strictly better in one respect — it is blind to
   coil current, eliminating the common-mode problem entirely — and worse in
   another: it measures a chord, not a gap, and needs its own calibration.

The decision point is protocol P3 acceptance. Choosing the fallbacks in
advance is the point: it prevents the failure mode where a bad signal is
tuned around for weeks instead of replaced.

### Risk 2 — capture range is small by construction

Simulated capture range is 1.78 mm, and it is set by actuator authority rather
than by the control law: PID, MPC and float32 network all reach the same
value. In practice the ball must be introduced into a ~1.8 mm window by hand.
This is a property of the rig, not a defect to be fixed, and it is reported as
such. A non-magnetic guide will be added to make the introduction repeatable.

### Risk 3 — thermal drift

The coil dissipates ~1.3 W at the bias point. Copper resistance rises 0.39 %/K,
so a 30 K rise moves $R$ by ~12 %, the equilibrium duty with it, and the ball
drifts. The integral term absorbs slow drift, but the operating point itself
shifts, which changes the plant. P1 quantifies this; it is not modelled.

### Risk 4 — single spares

One IRLZ44N and one 1N5822 are in hand (ten and five were ordered but arrived
partially), and **only two SS49E with no spare at all**. A single wiring error
on a divider destroys a sensor and stops the project until the next delivery.

## C. Scope limits of the result

- **The pot-core topology restricts the working gap to 2–3 mm.** Results do
  not transfer directly to open-solenoid rigs, where the pole is 2.45× slower
  and quantisation would have correspondingly more time to be wrong.
- **The plant model is linearised about a single operating point.** The MPC
  and the training data both inherit that linearisation; behaviour far from
  2.5 mm is extrapolation.
- **Steel hysteresis and ADC non-linearity are not modelled.**
- **The current is estimated, not measured, inside the loop.** The INA219
  needs 0.5 ms per reading against a 1 ms period, so the third network input
  comes from a first-order observer driven by the commanded duty. The
  simulation uses the same observer rather than the true current, so the
  figures are not optimistic on this account — but the observer's time
  constant is itself an assumption until P2 measures it, and a wrong
  $\tau_e$ makes the third network input wrong. A 0.1 Ω shunt on ADC1 would
  remove the dependency entirely and is the obvious next board revision.
- **Quantisation is symmetric per-tensor with float biases.** Per-channel
  quantisation or a fully integer bias path would give different numbers; the
  scheme studied here is the simplest one that runs, not the best one
  available.

## D. What would falsify the headline claim

The simulated finding is that int8 costs 1.33× in hold precision, nothing in
settling time, and 25 % of the capture range.

It would be falsified if, on the bench:

- int8 and float32 capture ranges come out equal within measurement error —
  which would mean the simulated loss is an artefact of the noiseless
  extrapolation region rather than of quantisation;
- or int8 settling time degrades measurably, which would mean the dynamics
  are not as robust to coefficient error as the simulation suggests.

Both outcomes are publishable, and the protocol records the prediction in
advance precisely so that either can be told apart from a post-hoc adjustment.
