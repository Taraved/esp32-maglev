#!/usr/bin/env python3
"""
Fit the position calibration curve / аппроксимация калибровочной кривой.

Input : data/calibration/run_*.csv following the schema in
        data/calibration/hall_calibration_TEMPLATE.csv
Output: the polynomial coefficients to paste into the firmware
        (CAL_C0..CAL_C2 in firmware/04_control_loop) and a figure.

Two numbers matter beyond the fit itself:

  * the residual RMS of the fit, which sets the floor on the position
    accuracy and therefore on every RMS figure in the comparison table;
  * the common-mode slope d(diff)/d(duty) at a fixed gap, which is the
    leakage of coil current into the position signal. The differential pair
    exists to make this small; whatever is left has to be compensated in
    software and reported in the limitations.

Два числа важны не меньше самой аппроксимации: остаточное СКО (нижняя граница
точности измерения положения) и наклон d(diff)/d(duty) при фиксированном
зазоре — остаточная наводка тока катушки в сигнал положения.
"""

import glob
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
CAL = os.path.join(HERE, "..", "data", "calibration")
FIG = os.path.join(HERE, "..", "docs", "figures")


def load(pattern="run_*.csv"):
    files = sorted(glob.glob(os.path.join(CAL, pattern)))
    if not files:
        return None
    rows = []
    for fn in files:
        rows.append(np.genfromtxt(fn, delimiter=",", names=True, comments="#"))
    return np.concatenate(rows) if len(rows) > 1 else rows[0]


def main():
    d = load()
    if d is None:
        print("no measurement files in data/calibration/ yet.")
        print("run firmware/02_hall_read, save the output as run_YYYYMMDD.csv,")
        print("then re-run this script. Template and schema:")
        print("  data/calibration/hall_calibration_TEMPLATE.csv")
        return 1

    gap, diff, duty = d["gap_mm"], d["diff"], d["duty"]
    ok = np.isfinite(gap) & np.isfinite(diff)
    gap, diff, duty = gap[ok], diff[ok], duty[ok]

    # calibration curve at the lowest duty (least current leakage)
    base = duty == duty.min()
    c = np.polyfit(diff[base], gap[base], 2)
    resid = gap[base] - np.polyval(c, diff[base])
    rms_um = float(np.sqrt(np.mean(resid ** 2)) * 1e3)

    # common-mode leakage: slope of diff vs duty at each gap
    slopes = []
    for g in np.unique(gap):
        sel = gap == g
        if sel.sum() > 2 and np.ptp(duty[sel]) > 0:
            slopes.append(np.polyfit(duty[sel], diff[sel], 1)[0])
    leak = float(np.mean(slopes)) if slopes else float("nan")

    print(f"gap_mm = {c[0]:+.6e}*d^2 {c[1]:+.6e}*d {c[2]:+.6f}")
    print(f"  paste into firmware: CAL_C2={c[0]:.6e}f CAL_C1={c[1]:.6e}f CAL_C0={c[2]:.6f}f")
    print(f"residual RMS            : {rms_um:.1f} um")
    print(f"common-mode leakage     : {leak:+.4f} counts per duty unit")
    print(f"  -> {abs(leak) * 2047 * abs(c[1]) * 1e3:.1f} um of apparent motion "
          f"over the full duty range")

    fig, ax = plt.subplots(figsize=(8, 5), dpi=170, facecolor="#0b0f19")
    ax.set_facecolor("#131b2e")
    ax.scatter(diff[base], gap[base], s=28, color="#38bdf8", label="measured")
    xs = np.linspace(diff[base].min(), diff[base].max(), 200)
    ax.plot(xs, np.polyval(c, xs), color="#f97316", linewidth=2,
            label=f"quadratic fit, residual {rms_um:.1f} µm RMS")
    ax.grid(color="#233554", linewidth=0.7)
    ax.set_xlabel("differential Hall signal, ADC counts", color="#94a3b8")
    ax.set_ylabel("air gap, mm", color="#94a3b8")
    ax.set_title("Position calibration", color="#f8fafc", fontweight="bold")
    ax.tick_params(colors="#94a3b8")
    ax.legend(facecolor="#131b2e", edgecolor="#233554", labelcolor="#f8fafc")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_calibration.png"), facecolor="#0b0f19")
    print("saved docs/figures/fig_calibration.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
