# Analysis

The simulation pipeline. Every number in the README that is not a physical
constant comes from here, and each script prints what it computes so the
results can be checked rather than trusted.

```bash
pip install -r requirements.txt
python3 plant_model.py            # parameter table, instant
python3 simulate_controllers.py   # ~90 s: MPC, training, quantisation, metrics
python3 export_weights.py         # writes the firmware headers
python3 make_figures.py           # writes the report figures
python3 fit_calibration.py        # once bench calibration data exists
```

| File | Role |
|---|---|
| `plant_model.py` | Physical parameters and linearisation. Nothing measured — every value is computed from geometry, material data or a stated design decision |
| `simulate_controllers.py` | Non-linear plant, PID, condensed-QP MPC, MLP training, int8 quantisation, closed-loop metrics |
| `export_weights.py` | Trained network → `firmware/05_nn_controller/nn_weights.h` and `nn_float.h` |
| `make_figures.py` | Figures for the report |
| `fit_calibration.py` | Position calibration fit; reports the residual and the residual current-to-position leakage |

## What the pipeline does

1. **Plant.** Gap, velocity and coil current integrated with RK4 at 20 µs,
   zero-order hold on duty at 1 kHz. The diode is modelled by clamping the
   current at zero.
2. **Sensor.** The controller never sees the true state. Position is a
   quantised, noisy estimate (σ = 4 µm, 2 µm LSB) with a first-order filter on
   the derivative channel. Coil current is **not** taken from the plant either:
   it comes from the same first-order observer the firmware runs, because the
   INA219 needs 0.5 ms per reading against a 1 ms period. Handing the network
   the true current would give it information the hardware cannot provide.
   **Both controller tunings were done with this model enabled** — see below.
3. **MPC.** 40-step horizon, condensed QP with input bounds, solved by bounded
   least squares. About 40 ms per step on a PC, which is why it cannot run on
   the microcontroller.
4. **Dataset.** Closed-loop MPC trajectories plus a uniform sample of the
   surrounding state box. Trajectories alone collapse onto a thin manifold and
   the network then extrapolates badly after a disturbance.
5. **Network.** 3-16-16-1, tanh, trained to imitate the MPC policy.
6. **Quantisation.** Symmetric per-tensor int8 weights, int32 accumulator,
   activations rescaled to int8 after each tanh. The numpy implementation
   mirrors the C code in `firmware/05_nn_controller/nn_int8.h` exactly.
7. **Metrics.** Eight noise realisations per controller; RMS hold error,
   settling time to ±50 µm, and capture range by bisection.

## Why the noise model is not optional

Tuning the PID on a noiseless plant gives Kp = 1600, Kd = 12 and a beautiful
step response. The same gains on the noise model produce **134 µm** of RMS
jitter, because a large derivative gain amplifies ADC noise. Re-tuning with
noise enabled gives Kp = 400, Kd = 4 and **2.36 µm**.

A 57× difference in the headline metric, produced entirely by whether the
simulation was honest about the signal chain. The MPC weights were selected
the same way, for the same reason: comparing a noise-aware PID against a
noise-naive MPC would have been a rigged comparison.

## What these results are and are not

They are simulation. They are labelled as simulation everywhere they appear.
The predictions are recorded in
[`../data/results/controller_comparison_TEMPLATE.csv`](../data/results/controller_comparison_TEMPLATE.csv)
before the bench experiment, so that a disagreement stays visible.
