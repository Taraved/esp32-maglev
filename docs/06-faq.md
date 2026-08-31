# 06 — FAQ: questions a reviewer will ask

*[Русская версия](06-faq.ru.md)*

---

## About the result

### What is the actual finding, in one sentence?

In simulation, int8 quantisation of the neural controller costs 1.33× in hold
precision and **25 % of the capture range**, while costing nothing in settling
time — and the capture-range loss does not follow from the open-loop
approximation error, so a quantisation report that measures only tracking
accuracy would miss it.

---

## About the control design

### Why not TinyMPC, micro-OSQP or another embedded QP solver?

They exist and they are fast — TinyMPC's ADMM would plausibly solve this
40-step, 3-state problem on an ESP32-S3 in a few hundred microseconds.

Two reasons:

1. **Determinism.** An iterative solver has a variable iteration count. On a
   plant with an 11.3 ms divergence constant and a 1 ms hard deadline, a
   worst-case overrun during a disturbance is a dropped ball, and the
   worst case is exactly when the disturbance is largest. A fixed 320-MAC
   network has a constant, measurable step time by construction.
2. **The MPC is not the goal.** It is the reference policy. The research
   question is what quantisation costs in a closed loop, and that needs a
   policy that can be quantised — which a QP solver cannot be.

A direct comparison against an embedded solver is a legitimate follow-up and
would strengthen the work.

### How is radial stability handled? Earnshaw's theorem forbids passive 3-axis stability.

Correct — the active loop controls the vertical axis only.

Near the face of a pot-core magnet the pole geometry (central core, outer
ring) produces a radial field gradient that centres the ball toward the axis
of symmetry at small gaps. This helps but does not guarantee stability: under
a large lateral disturbance the ball can be captured by the outer ring instead.

The planned mitigation is mechanical, not magnetic: a non-magnetic guide
(PTFE or acrylic) around the working region during calibration. This is a
known limitation of the rig, not a solved problem, and it is one of the
reasons the capture-range metric is measured at all.

### Why 1 kHz and not faster?

The unstable pole is 88.6 rad/s, giving a divergence time constant of 11.3 ms,
so 1 kHz provides 11.3 samples per time constant. That is adequate but not
generous. The limit is not the CPU — the int8 network needs 320 MACs — but the
sensing chain: 8× ADC oversampling plus the derivative filter already consume
a meaningful fraction of the period, and increasing the rate without improving
the sensor would only sample noise faster.

If protocol P3 shows a cleaner signal than assumed, 2 kHz is a straightforward
change.

### Why does the PID use Kp = 400 rather than the value that looks better in simulation?

Because the value that looks better is measured on a noiseless signal. A grid
search on the clean plant returns Kp = 1600, Kd = 12 with an excellent step
response; the same gains with a realistic ADC noise model produce **134 µm** of
RMS jitter, against 2.36 µm for Kp = 400, Kd = 4.

A 57× difference in the headline metric, decided entirely by whether the
simulation was honest about the signal chain. The MPC weights were selected
the same way and for the same reason: comparing a noise-aware PID against a
noise-naive MPC would have been a rigged comparison.

---

## About the plant

### Eddy currents: the core is solid steel, not laminated. At 20 kHz that matters.

It does. A solid mild-steel core supports eddy currents that oppose flux
change, so B(t) lags i(t) and the force response is slower than the
instantaneous $F \propto (i/x)^2$ model assumes.

The current model does not include this. Protocol P4 identifies the plant from
step-response data, and it is designed to expose exactly this: if the measured
pole is slower than the computed 88.6 rad/s, or a phase lag appears that the
electrical time constant alone cannot explain, a first-order magnetic lag
$1/(T_{eddy}s + 1)$ enters the model. The disagreement would be a result, and
the protocol records the prediction in advance so that it can be recognised
as one.

### Is the inverse-square force law valid at a 2.5 mm gap on a pot-core magnet?

This is the weakest assumption in the model, and it is stated as such in the
limitations. The law is derived for a simple air gap; at 2.5 mm on this
geometry the flux is partly shunted across the face, and local saturation at
the contact region is likely.

$k$ is currently fixed by construction — chosen so that equilibrium holds at
the design point — rather than identified. Protocol P4 fits it from data. If
the fitted pole disagrees with the computed one by more than 30 %, that is
reported rather than corrected away.

### Why 2.5 mm and not a larger gap with the M4 pole extender?

The extender (option B) would relax the pole to roughly 50 rad/s and make the
sensing problem easier. It is deliberately held in reserve because it modifies
the actuator: the analysis in [`01`](01-actuator-analysis.md) applies to the
stock part, and using the stock part keeps the result comparable with other
work using the same class of magnet. If protocol P3 fails, the extender is the
first fallback.

---

## About the network

### Why tanh and not ReLU?

ReLU has a discontinuous derivative at each activation boundary. In a feedback
loop this puts kinks in the control surface, and the controller crosses those
boundaries continuously while holding position — producing high-frequency
content in the duty signal that a smooth activation avoids. Tanh gives a $C^\infty$
control surface at a cost of roughly 2 µs per step on the S3's FPU.

### Why is the quantisation hybrid? The matrix multiplies are int8 but tanh and the biases are float.

Because the ESP32-S3 has a single-precision FPU, and the arithmetic being
studied is the arithmetic that dominates: 320 multiply-accumulates in int8
against 32 tanh evaluations in float. Storing weights as int8 is what saves
memory (452 B against 1412 B); converting 32 transcendental functions to fixed
point would save microseconds and add a second quantisation scheme to reason
about.

This is a choice, not a necessity, and it is stated in the limitations: a
fully integer path — including per-channel scales and an integer bias — would
give different numbers. The scheme studied here is the simplest one that runs.

### Why int8 and not int16?

int8 is where the interesting failure lives. int16 on this network would be
close to lossless and the experiment would have no signal. If int8 turns out
to cost more than an application can tolerate, int16 is the obvious next
measurement and the pipeline supports it with a one-line change.

### 353 parameters is tiny. Does the network actually do anything?

It reproduces a 40-step constrained QP to within 0.12 µm RMS of closed-loop
performance. The policy it imitates is close to piecewise-affine over the
operating region, which is exactly what a small tanh network approximates
well. Size is the point: the question is what happens at the small end, where
quantisation error is not negligible.

---

## About the implementation

### Why ESP32-S3 rather than an STM32 or a Teensy?

Dual core is the deciding feature: the control loop is pinned to core 0 and
the Wi-Fi telemetry to core 1, so the network stack cannot steal a control
tick. On a single-core MCU it eventually would, and on an 11.3 ms unstable
plant one missed tick is a dropped ball.

The S3 also brought constraints worth documenting: GPIO 35/36/37 are consumed
by the octal PSRAM, and ADC2 stops working when Wi-Fi is enabled — which is
why every analogue input is on ADC1.

### The current is estimated, not measured. Doesn't that weaken the result?

It is a real limitation, and it is now handled consistently. The INA219 needs
0.5 ms per I²C read against a 1 ms period, so the third network input comes
from a first-order observer driven by the commanded duty.

**The simulation uses the same observer**, not the true current — feeding the
network the true current would give it information the hardware cannot
provide. The observer's time constant is itself an assumption until protocol
P2 measures it.

The clean fix is hardware: a 0.1 Ω shunt read by ADC1 would give a fast
current measurement and remove the dependency entirely. That is the obvious
next board revision.

### Why write the int8 inference by hand instead of using TFLite Micro?

353 parameters do not justify tens of kilobytes of interpreter runtime. More
importantly, the step time must be bounded and measurable — GPIO 17 is toggled
around the computation so it can be read directly on a scope — and the
quantisation scheme is the object of study, so it has to be visible rather
than hidden behind a framework's converter.
