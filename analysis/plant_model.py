#!/usr/bin/env python3
"""
Plant model of the magnetic levitation rig / Модель объекта управления.

Everything in this file is COMPUTED from first principles and datasheet
figures. Nothing here is a measured value: measured quantities live in
../data/ and are marked as such.

Все величины здесь ВЫЧИСЛЯЮТСЯ из физики и паспортных данных. Ни одно
число в этом файле не является измеренным: измерения лежат в ../data/.

Usage:
    python3 plant_model.py            # print the parameter table
"""

from dataclasses import dataclass, asdict
import math

G = 9.80665          # m/s^2, standard gravity
RHO_BEARING_STEEL = 7810.0   # kg/m^3, GOST SHKh15 / AISI 52100


@dataclass
class PlantParams:
    """Design parameters of the rig. Sources are given per field."""

    # --- object under control -------------------------------------------
    d_ball: float = 10.0e-3      # m, sphere diameter (SHKh15, purchased)
    rho: float = RHO_BEARING_STEEL

    # --- operating point --------------------------------------------------
    # Chosen in docs/01-actuator-analysis: the pot-core topology of the
    # JF-XP25x20 shunts flux at the face, so the usable gap is 2-3 mm,
    # not the 10-15 mm assumed in the textbook literature.
    x0: float = 2.5e-3           # m, nominal air gap

    # Bias current at equilibrium. Chosen at ~55 % of the maximum coil
    # current so that the controller has symmetric authority in both
    # directions (it can both increase and decrease the force).
    i0: float = 0.25             # A

    # --- actuator (JF-XP25x20) -------------------------------------------
    U_supply: float = 12.0       # V, nameplate
    R_coil: float = 27.0         # ohm, ASSUMED (datasheet class 25-30);
                                 # to be replaced by the measured value
    L_coil: float = 40.0e-3      # H, ASSUMED (pot-core, class 20-60 mH);
                                 # to be replaced by the measured value

    # --- control loop -----------------------------------------------------
    f_s: float = 1000.0          # Hz, control loop rate
    f_pwm: float = 20000.0       # Hz, LEDC carrier
    pwm_bits: int = 11           # LEDC resolution

    # ---------------------------------------------------------------------
    @property
    def m(self) -> float:
        """Ball mass, kg."""
        v = (4.0 / 3.0) * math.pi * (self.d_ball / 2.0) ** 3
        return self.rho * v

    @property
    def weight(self) -> float:
        """Gravity force on the ball, N."""
        return self.m * G

    @property
    def k(self) -> float:
        """
        Force constant of F(i, x) = k (i/x)^2, N*m^2/A^2.

        Fixed by requiring equilibrium F(i0, x0) = m*g at the chosen
        operating point. This is a *calibration by construction*: the real
        k will be identified from step-response data (docs/03, protocol P4)
        and this value is the design-time estimate.
        """
        return self.weight * self.x0 ** 2 / self.i0 ** 2

    def force(self, i: float, x: float) -> float:
        """Attraction force, N."""
        return self.k * (i / x) ** 2

    # --- linearisation about (i0, x0) ------------------------------------
    @property
    def k_x(self) -> float:
        """dF/dx at the operating point, N/m (negative: force falls with gap)."""
        return -2.0 * self.weight / self.x0

    @property
    def k_i(self) -> float:
        """dF/di at the operating point, N/A."""
        return 2.0 * self.weight / self.i0

    @property
    def pole(self) -> float:
        """
        Unstable open-loop pole, rad/s.

        Linearised: m*d2(dx) = -k_x*dx - k_i*di  =>  s^2 = 2g/x0.
        """
        return math.sqrt(2.0 * G / self.x0)

    @property
    def tau_unstable(self) -> float:
        """Divergence time constant 1/pole, s."""
        return 1.0 / self.pole

    @property
    def tau_electrical(self) -> float:
        """Coil electrical time constant L/R, s."""
        return self.L_coil / self.R_coil

    @property
    def i_max(self) -> float:
        """Maximum coil current at full duty, A."""
        return self.U_supply / self.R_coil

    @property
    def samples_per_tau(self) -> float:
        """Control samples inside one divergence time constant."""
        return self.f_s * self.tau_unstable

    def state_space(self):
        """
        Continuous-time A, B for state [gap error, gap rate], input = current.
        Returns nested lists (no numpy needed for the summary table).
        """
        a = [[0.0, 1.0], [self.pole ** 2, 0.0]]
        b = [[0.0], [-self.k_i / self.m]]
        return a, b


def summary(p: PlantParams) -> str:
    a, b = p.state_space()
    rows = [
        ("Ball mass m", f"{p.m * 1e3:.2f}", "g", "computed from Ø10 mm, ρ=7810 kg/m³"),
        ("Weight m·g", f"{p.weight * 1e3:.1f}", "mN", "computed"),
        ("Operating gap x₀", f"{p.x0 * 1e3:.1f}", "mm", "design choice, see docs/01"),
        ("Bias current i₀", f"{p.i0:.2f}", "A", "design choice, ~55 % of i_max"),
        ("Max coil current", f"{p.i_max:.2f}", "A", f"{p.U_supply} V / {p.R_coil} Ω (R assumed)"),
        ("Force constant k", f"{p.k * 1e6:.2f}", "µN·m²/A²", "from equilibrium at (i₀, x₀)"),
        ("∂F/∂x", f"{p.k_x:.1f}", "N/m", "computed = −2mg/x₀"),
        ("∂F/∂i", f"{p.k_i:.3f}", "N/A", "computed = 2mg/i₀"),
        ("Unstable pole", f"{p.pole:.1f}", "rad/s", "computed = √(2g/x₀)"),
        ("Divergence τ", f"{p.tau_unstable * 1e3:.1f}", "ms", "computed = 1/pole"),
        ("Electrical τ = L/R", f"{p.tau_electrical * 1e3:.2f}", "ms", "L, R assumed"),
        ("Loop rate f_s", f"{p.f_s:.0f}", "Hz", "design choice"),
        ("Samples per τ", f"{p.samples_per_tau:.1f}", "—", "computed"),
    ]
    w = max(len(r[0]) for r in rows)
    out = ["", "PLANT PARAMETERS (all computed, none measured)", "=" * 78]
    for name, val, unit, src in rows:
        out.append(f"{name:<{w}}  {val:>9}  {unit:<10}  {src}")
    out += ["", "Linearised state space  ẋ = Ax + Bu,  x = [gap error, rate], u = current",
            f"  A = {a}", f"  B = {b}", ""]

    # comparison against the textbook operating point
    p15 = PlantParams(x0=15.0e-3)
    out += ["Why the operating point matters:",
            f"  x₀ = 2.5 mm  ->  pole {p.pole:5.1f} rad/s, τ = {p.tau_unstable*1e3:5.1f} ms",
            f"  x₀ = 15 mm   ->  pole {p15.pole:5.1f} rad/s, τ = {p15.tau_unstable*1e3:5.1f} ms",
            f"  the plant is {p15.tau_unstable / p.tau_unstable:.2f}x faster at the gap this "
            f"actuator actually permits", ""]
    return "\n".join(out)


if __name__ == "__main__":
    print(summary(PlantParams()))
