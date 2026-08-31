#!/usr/bin/env python3
"""
Figures for the report / графики для отчёта.

Reads  data/results/traces.npz, simulation_summary.json
Writes docs/figures/fig_step_response.png  — the headline plot of the project
       docs/figures/fig_quantisation.png   — float32 vs int8, зум на разницу
       docs/figures/fig_plant.png          — open-loop divergence and force law
"""

import json
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from plant_model import PlantParams, G

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "data", "results")
FIG = os.path.join(HERE, "..", "docs", "figures")

BG, PANEL, INK, DIM, GRID = "#0b0f19", "#131b2e", "#f8fafc", "#94a3b8", "#233554"
COL = {"PID": "#38bdf8", "MPC_(float64,_PC)": "#a855f7",
       "NN_float32": "#22c55e", "NN_int8": "#f97316"}
NICE = {"PID": "PID", "MPC_(float64,_PC)": "MPC (float64, PC)",
        "NN_float32": "NN float32", "NN_int8": "NN int8"}
P = PlantParams()


def style(ax, xl, yl, title=None):
    ax.set_facecolor(PANEL)
    ax.grid(True, color=GRID, linewidth=0.7, alpha=0.7)
    ax.set_axisbelow(True)
    for s in ax.spines.values():
        s.set_color(GRID)
    ax.tick_params(colors=DIM, labelsize=9)
    ax.set_xlabel(xl, color=DIM, fontsize=10)
    ax.set_ylabel(yl, color=DIM, fontsize=10)
    if title:
        ax.set_title(title, color=INK, fontsize=12, fontweight="bold", pad=10)


def fig_step():
    tr = np.load(os.path.join(RES, "traces.npz"))
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 8), dpi=170,
                                 facecolor=BG, sharex=True,
                                 gridspec_kw=dict(height_ratios=[3, 2]))
    for k in ["PID", "MPC_(float64,_PC)", "NN_float32", "NN_int8"]:
        if k not in tr:
            continue
        d = tr[k]
        t, x, duty = d[:, 0] * 1e3, d[:, 1] * 1e3, d[:, 3]
        sel = (t > 480) & (t < 700)
        a1.plot(t[sel] - 500, x[sel], color=COL[k], linewidth=1.7, label=NICE[k])
        a2.plot(t[sel] - 500, duty[sel], color=COL[k], linewidth=1.4)

    a1.axhline(P.x0 * 1e3, color=DIM, linewidth=0.9, linestyle="--")
    a1.axhspan(P.x0 * 1e3 - 0.05, P.x0 * 1e3 + 0.05, color="#334155", alpha=0.35,
               label="±50 µm settling band")
    a1.axvline(0, color="#fbbf24", linewidth=1.2, linestyle=":")
    a1.text(2, P.x0 * 1e3 + 0.30, "velocity impulse 50 mm/s", color="#fbbf24", fontsize=9)
    style(a1, "", "air gap, mm",
          "Simulated disturbance rejection — identical impulse, four controllers")
    a1.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=INK, fontsize=9, loc="upper right")
    style(a2, "time after the impulse, ms", "PWM duty")
    a2.set_ylim(0, 1)
    fig.text(0.5, 0.012,
             "Simulation with the sensor-noise model enabled (σ = 4 µm, 2 µm quantisation). "
             "Not a bench measurement.",
             ha="center", color=DIM, fontsize=9.5)
    fig.tight_layout(rect=[0, 0.035, 1, 1])
    fig.savefig(os.path.join(FIG, "fig_step_response.png"), facecolor=BG,
                bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)
    print("saved fig_step_response.png")


def fig_quant():
    tr = np.load(os.path.join(RES, "traces.npz"))
    with open(os.path.join(RES, "simulation_summary.json")) as f:
        summ = json.load(f)
    f32, i8 = tr["NN_float32"], tr["NN_int8"]
    n = min(len(f32), len(i8))
    t = f32[:n, 0] * 1e3
    e32 = (f32[:n, 1] - P.x0) * 1e6
    e8 = (i8[:n, 1] - P.x0) * 1e6

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5), dpi=170, facecolor=BG,
                                 gridspec_kw=dict(width_ratios=[3, 2]))
    sel = (t > 480) & (t < 760)
    a1.plot(t[sel] - 500, e32[sel], color=COL["NN_float32"], linewidth=1.8, label="float32")
    a1.plot(t[sel] - 500, e8[sel], color=COL["NN_int8"], linewidth=1.8, label="int8")
    a1.axhline(0, color=DIM, linewidth=0.8, linestyle="--")
    style(a1, "time after the impulse, ms", "gap error, µm",
          "The headline plot: same network, two arithmetics")
    a1.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=INK, fontsize=10)

    cl = summ["closed_loop"]
    names = ["NN float32", "NN int8"]
    rms = [cl[k]["rms_um"] for k in names]
    sd = [cl[k]["rms_sd"] for k in names]
    settle = [cl[k]["settling_ms"] for k in names]
    xs = np.arange(2)
    a2.bar(xs - 0.19, rms, 0.36, yerr=sd, capsize=4,
           color=[COL["NN_float32"], COL["NN_int8"]], label="RMS error, µm")
    a2b = a2.twinx()
    a2b.bar(xs + 0.19, settle, 0.36, color=[COL["NN_float32"], COL["NN_int8"]],
            alpha=0.45, label="settling, ms")
    a2b.tick_params(colors=DIM, labelsize=9)
    a2b.set_ylabel("settling time, ms", color=DIM, fontsize=10)
    for s in a2b.spines.values():
        s.set_color(GRID)
    a2.set_xticks(xs)
    a2.set_xticklabels(names, color=DIM, fontsize=10)
    style(a2, "", "RMS hold error, µm", "Cost of int8")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_quantisation.png"), facecolor=BG,
                bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)
    print("saved fig_quantisation.png")


def fig_plant():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.8), dpi=170, facecolor=BG)

    # force law at several currents
    x = np.linspace(1.0e-3, 8.0e-3, 400)
    for i, c in zip([0.15, 0.25, 0.35, 0.44], ["#334155", "#38bdf8", "#a855f7", "#f97316"]):
        a1.plot(x * 1e3, P.k * (i / x) ** 2 * 1e3, color=c, linewidth=1.8,
                label=f"i = {i:.2f} A")
    a1.axhline(P.weight * 1e3, color="#fbbf24", linewidth=1.3, linestyle="--")
    a1.text(5.6, P.weight * 1e3 + 3, "ball weight 40.1 mN", color="#fbbf24", fontsize=9)
    a1.plot([P.x0 * 1e3], [P.weight * 1e3], "o", color=INK, markersize=7, zorder=5)
    a1.annotate("operating point\n2.5 mm, 0.25 A", (P.x0 * 1e3, P.weight * 1e3),
                textcoords="offset points", xytext=(38, 30), color=INK, fontsize=9,
                arrowprops=dict(arrowstyle="->", color=INK, linewidth=1.1))
    a1.set_ylim(0, 260)
    style(a1, "air gap x, mm", "force F, mN", "Force law  F = k (i/x)²")
    a1.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=INK, fontsize=9)

    # open-loop divergence from a 10 um offset, both operating points
    for x0, c, lab in [(2.5e-3, "#f97316", "x₀ = 2.5 mm (this rig)"),
                       (15.0e-3, "#38bdf8", "x₀ = 15 mm (textbook)")]:
        pole = np.sqrt(2 * G / x0)
        t = np.linspace(0, 0.08, 300)
        a2.plot(t * 1e3, 10.0 * np.cosh(pole * t), color=c, linewidth=1.9, label=lab)
        a2.axvline(1e3 / pole, color=c, linewidth=1.0, linestyle=":")
    a2.set_yscale("log")
    a2.set_ylim(8, 5e3)
    a2.text(12.5, 1.4e3, "τ = 11.3 ms", color="#f97316", fontsize=9.5, fontweight="bold")
    a2.text(29, 1.4e3, "τ = 27.7 ms", color="#38bdf8", fontsize=9.5, fontweight="bold")
    style(a2, "time, ms", "gap deviation from 10 µm, µm",
          "Open-loop divergence: why the gap sets the loop rate")
    a2.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=INK, fontsize=9, loc="lower right")

    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_plant.png"), facecolor=BG,
                bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)
    print("saved fig_plant.png")


if __name__ == "__main__":
    fig_plant()
    fig_step()
    fig_quant()
