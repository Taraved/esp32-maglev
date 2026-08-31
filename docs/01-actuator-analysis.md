# 01 — Actuator field topology and its consequences for control

*[Русская версия](01-actuator-analysis.ru.md)*

---

## 1. The discrepancy

Textbook magnetic levitation places the equilibrium gap at
$x_0 = 10\dots15$ mm. On this hardware — a JF-XP25×20 at its nominal 12 V —
a Ø10 mm bearing-steel sphere is attracted only from **1–2 mm**.

A discrepancy of that size is not a tuning problem. It is a statement about
the actuator.

## 2. Why: pot-core topology

The JF-XP25×20 belongs to the class of **holding electromagnets**, not to the
class of open solenoids assumed in levitation literature.

```
   POT-CORE (JF-XP25x20)                 OPEN SOLENOID
      ┌───┬─────────┬───┐                   ┌──────────┐
      │ S │    N    │ S │                   │    N     │  <- pole N
      │   │ winding │   │                   │ ┌──────┐ │
      │   │         │   │                   │ │winding││
      └───┴────┬────┴───┘                   │ └──────┘ │
         ↓ ~2 mm ↓                          │    S     │  <- pole S
   flux closes across the face,             └────┬─────┘
   almost nothing reaches the air           field lines reach 15-20 mm
```

1. **Magnetic circuit.** The central cylindrical core is one pole; the outer
   steel cup is the opposite pole.
2. **Face gap.** The annular gap between them is only 1.5–2.0 mm, filled with
   potting compound.
3. **Reluctance.** Flux follows the path of least magnetic reluctance
   $R_m = l / (\mu_0 \mu_r S)$. Once the air gap to the ball exceeds ~2 mm,
   the external path is tens of times worse than the core-to-cup path directly
   across the face.
4. **Result.** The flux shunts at the face. Field lines barely penetrate more
   than 2–3 mm into the surrounding space, so there is nothing left at 15 mm
   to lift the ball with.

## 3. Why the nameplate 50 N is not available either

The rated 50 N (5 kg) is measured under conditions that the experiment does
not reproduce:

- **at zero gap**, with a ground contact surface;
- against a **thick flat plate** (≥ 5 mm) of soft magnetic steel that spans
  both the central core and the outer ring, closing the magnetic circuit with
  no air gap at all.

A Ø10 mm sphere touches a plane at a single geometric point. It closes no
magnetic circuit, and the small contact region saturates locally
($B_{sat} \approx 1.8$–2.0 T), which caps the achievable force far below the
nameplate value regardless of current.

## 4. Decision and its consequences

**Adopted (option A):** move the operating point to $x_0 = 2.0\dots3.0$ mm,
nominally **2.5 mm**.

The unstable pole depends only on the gap:

$$s_{\text{pole}} = \sqrt{\frac{2g}{x_0}}$$

| Gap | Pole | Divergence τ | Samples per τ at 1 kHz |
|---|---|---|---|
| **2.5 mm (adopted)** | **88.6 rad/s** | **11.3 ms** | **11.3** |
| 15 mm (textbook) | 36.2 rad/s | 27.7 ms | 27.7 |

The plant is **2.45× faster** than the case the literature describes. Four
design consequences follow directly, and none of them is a preference:

| Consequence | Why it is forced |
|---|---|
| Control loop ≥ 1 kHz, pinned to a dedicated core | 11.3 samples per divergence constant is already tight; Wi-Fi must not be able to steal a tick |
| Derivative filter capped at τ = 2 ms | filtering costs phase, and phase margin on an 11.3 ms unstable pole is scarce |
| Mechanical stand rigidity is a first-order requirement | 0.5 mm of backlash is 20 % of the working range |
| Capture range will be small | the region of attraction cannot exceed the few millimetres over which the field exists at all |

The last row is worth stating explicitly: the simulated capture range is
1.78 mm for every controller tested, identical across PID, MPC and the float32
network. It is limited by **actuator authority**, not by the control law. The
one configuration that reduces it further is int8 quantisation
(1.33 mm) — which is precisely why that metric is in the comparison table.

**Held in reserve (option B):** a steel M4 bolt, 6–8 mm long, threaded into
the centre of the face. This moves pole N forward relative to ring S,
separating the poles in space and extending field penetration to 6–8 mm.
It is the fallback if the differential Hall pair cannot resolve position at
2.5 mm; see [`05-limitations.md`](05-limitations.md#risk-1).

## 5. Why this belongs in a portfolio rather than a footnote

Most student levitation projects assume the open-solenoid force law, buy a
holding electromagnet because it is the cheap part with an impressive newton
rating, and then spend weeks trying to make a ball hover at 15 mm where no
field exists. The failure is usually attributed to controller tuning.

The analysis above is what changes the project from "the ball does not hover"
to a specified plant with a justified operating point, a computed pole, and a
sampling rate derived from that pole rather than chosen by habit.

**Verification status.** The 1–2 mm attraction distance is an observation made
with the actual magnet and ball. The reluctance argument explaining it is
analysis, not measurement — the flux distribution has not been measured, and a
direct measurement would require a gaussmeter the project does not have. The
force law and the identified pole are tested quantitatively in protocol P4;
should the measured pole disagree with 88.6 rad/s by more than 30 %, that
disagreement is itself reported.
