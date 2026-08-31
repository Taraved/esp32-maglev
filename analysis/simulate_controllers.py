#!/usr/bin/env python3
"""
Closed-loop simulation of the four controllers / Симуляция четырёх регуляторов.

Pipeline:
    1. non-linear plant (gap, velocity, coil current) integrated with RK4
    2. PID tuned by hand on the non-linear plant
    3. linear MPC (condensed QP with input bounds) on the linearised plant
    4. MLP trained to imitate the MPC (explicit-MPC approximation), float32
    5. the same MLP quantised to int8 and executed with integer arithmetic

Every number this script prints is a SIMULATION result, not a bench
measurement. Bench measurements go to ../data/results/ once the rig runs.

Каждое число, которое печатает скрипт, получено СИМУЛЯЦИЕЙ, а не измерением
на стенде. Измерения появятся в ../data/results/ после запуска стенда.

Usage:
    python3 simulate_controllers.py
"""

import json
import math
import os

import numpy as np
from scipy.optimize import lsq_linear
from scipy.linalg import expm

from plant_model import PlantParams, G

rng = np.random.default_rng(20260831)
P = PlantParams()
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "results")
FIG = os.path.join(HERE, "..", "docs", "figures")

TS = 1.0 / P.f_s          # control period, 1 ms
DT = 20e-6                # integration step, 20 us
SUB = int(round(TS / DT))
DUTY0 = P.i0 * P.R_coil / P.U_supply     # duty at equilibrium


# =============================================================================
# 1. plant
# =============================================================================
def derivs(s, duty):
    """s = [gap x (m), velocity v (m/s), coil current i (A)]."""
    x, v, i = s
    x = max(x, 0.2e-3)                       # ball cannot pass the pole face
    f = P.k * (i / x) ** 2
    return np.array([v,
                     G - f / P.m,
                     (duty * P.U_supply - P.R_coil * i) / P.L_coil])


def step(s, duty):
    """One control period, RK4 sub-stepped, zero-order hold on duty."""
    for _ in range(SUB):
        k1 = derivs(s, duty)
        k2 = derivs(s + 0.5 * DT * k1, duty)
        k3 = derivs(s + 0.5 * DT * k2, duty)
        k4 = derivs(s + DT * k3, duty)
        s = s + (DT / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
        s[2] = max(s[2], 0.0)                # diode prevents reverse current
    return s


# =============================================================================
# 2. linearised discrete model (used by MPC and as the NN feature frame)
# =============================================================================
# state z = [gap error e, rate de, current deviation di], input = duty deviation
Ac = np.array([[0.0, 1.0, 0.0],
               [2 * G / P.x0, 0.0, -2 * G / P.i0],
               [0.0, 0.0, -P.R_coil / P.L_coil]])
Bc = np.array([[0.0], [0.0], [P.U_supply / P.L_coil]])

M = np.zeros((4, 4))
M[:3, :3] = Ac
M[:3, 3:] = Bc
Md = expm(M * TS)
Ad, Bd = Md[:3, :3], Md[:3, 3:]

N_HORIZON = 40
# Weights are inverse squared tolerances. They were selected by a grid search
# run WITH the sensor-noise model enabled, exactly as the PID gains were, so
# that the comparison between the two is fair: an MPC tuned on a noiseless
# model looks superb in simulation and then amplifies ADC noise on the bench.
# Веса подобраны сеткой ПРИ ВКЛЮЧЁННОЙ модели шума — так же, как и ПИД,
# иначе сравнение двух регуляторов некорректно.
Q = np.diag([4.0e8, 4.0e2, 4.0e2])
R_W = 1.0e3


def build_condensed():
    """Stack the prediction over the horizon: Z = Sx z0 + Su U."""
    n, m = 3, 1
    Sx = np.zeros((N_HORIZON * n, n))
    Su = np.zeros((N_HORIZON * n, N_HORIZON * m))
    Ak = np.eye(n)
    for r in range(N_HORIZON):
        Ak = Ak @ Ad if r else Ad.copy()
        Sx[r * n:(r + 1) * n, :] = Ak
        for c in range(r + 1):
            blk = np.linalg.matrix_power(Ad, r - c) @ Bd
            Su[r * n:(r + 1) * n, c:c + 1] = blk
    return Sx, Su


SX, SU = build_condensed()
QS = np.kron(np.eye(N_HORIZON), np.sqrt(Q))
RS = math.sqrt(R_W) * np.eye(N_HORIZON)
A_LS = np.vstack([QS @ SU, RS])


def mpc(z0):
    """Solve the bounded QP, return the first duty deviation."""
    b = np.concatenate([-(QS @ (SX @ z0)), np.zeros(N_HORIZON)])
    lo, hi = -DUTY0, 1.0 - DUTY0
    sol = lsq_linear(A_LS, b, bounds=(lo, hi), max_iter=60, tol=1e-8)
    return float(sol.x[0])


# =============================================================================
# 3. controllers
# =============================================================================
class PID:
    """
    PD with a small I term, as an unstable plant demands.

    Gains were found by a grid search run WITH the sensor-noise model
    enabled. Tuning without noise gives Kp = 1600, Kd = 12, which looks
    excellent on a clean signal and then amplifies ADC noise into a 134 um
    RMS jitter on the real signal chain. This is the single most common way
    to fool yourself in simulation, so the noise model is not optional.

    Коэффициенты подобраны сеткой ПРИ ВКЛЮЧЁННОЙ модели шума датчика.
    Настройка без шума даёт Kp = 1600, Kd = 12 — прекрасно выглядит на
    чистом сигнале и даёт 134 мкм дрожания на реальном тракте.
    """
    KP, KD, KI = 400.0, 4.0, 400.0

    def __init__(self):
        self.integ = 0.0

    def __call__(self, e, de, _i):
        self.integ = float(np.clip(self.integ + e * TS, -2e-3, 2e-3))
        return float(np.clip(DUTY0 + self.KP * e + self.KD * de + self.KI * self.integ,
                             0.0, 1.0))


class MPCController:
    def __call__(self, e, de, i):
        return float(np.clip(DUTY0 + mpc(np.array([e, de, i - P.i0])), 0.0, 1.0))


# =============================================================================
# 4. dataset from the MPC, over the reachable state box
# =============================================================================
def build_dataset(n_traj=40, n_uniform=3000):
    """
    Two sources, as is standard for explicit-MPC imitation:

      * closed-loop MPC trajectories from randomised initial conditions —
        these cover the states the controller actually visits;
      * a uniform sample of the surrounding box — this keeps the network
        sane when a disturbance throws the plant outside the trajectories.

    Two sources are needed because trajectories alone collapse onto a thin
    manifold and the network then extrapolates badly after a kick.
    """
    Xs, ys = [], []
    ctrl = MPCController()
    for t in range(n_traj):
        x_init = P.x0 + rng.uniform(-0.5e-3, 0.9e-3)
        log, ok = run(ctrl, t_end=0.45, kick=float(rng.uniform(-0.06, 0.06)),
                      t_kick=0.20, x_init=x_init, seed=1000 + t)
        if not ok:
            continue
        e_prev = log[0, 1] - P.x0
        for row in log:
            e = row[1] - P.x0
            de = (e - e_prev) / TS
            e_prev = e
            Xs.append([e, de, row[4] - P.i0])   # observer, not truth
    Xt = np.array(Xs)

    e = rng.uniform(-0.45e-3, 0.45e-3, n_uniform)
    de = rng.uniform(-0.35, 0.35, n_uniform)
    di = rng.uniform(-0.12, 0.12, n_uniform)
    Xu = np.stack([e, de, di], axis=1)

    X = np.vstack([Xt, Xu])
    y = np.array([mpc(z) for z in X])
    return X.astype(np.float32), y.astype(np.float32)


# feature scaling: fixed, known at compile time, so the MCU does not divide
SCALE = np.array([0.45e-3, 0.35, 0.12], dtype=np.float32)  # e[m], de[m/s], di[A]
U_SCALE = np.float32(0.5)                                   # duty deviation


def train_mlp(X, y, hidden=16, epochs=4000):
    import torch
    import torch.nn as nn

    torch.manual_seed(7)
    Xn = torch.tensor(X / SCALE)
    yn = torch.tensor((y / U_SCALE).reshape(-1, 1))

    net = nn.Sequential(nn.Linear(3, hidden), nn.Tanh(),
                        nn.Linear(hidden, hidden), nn.Tanh(),
                        nn.Linear(hidden, 1))
    opt = torch.optim.Adam(net.parameters(), lr=1.2e-2)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, epochs)
    lossf = nn.MSELoss()
    for _ in range(epochs):
        opt.zero_grad()
        loss = lossf(net(Xn), yn)
        loss.backward()
        opt.step()
        sched.step()
    w = [p.detach().numpy().astype(np.float32) for p in net.parameters()]
    return w, float(loss.item())


# --- float32 inference, plain numpy (mirrors the C code in firmware/) --------
def nn_float(w, z):
    h = np.tanh(w[0] @ (z / SCALE) + w[1])
    h = np.tanh(w[2] @ h + w[3])
    return float((w[4] @ h + w[5])[0]) * U_SCALE


# --- int8 inference: symmetric per-tensor, int32 accumulator ----------------
def quantise(w):
    """Return int8 weights, int32 biases and the scale factors."""
    q = {}
    for idx, name in ((0, "w1"), (2, "w2"), (4, "w3")):
        W = w[idx]
        s = np.max(np.abs(W)) / 127.0
        q[name] = np.clip(np.round(W / s), -127, 127).astype(np.int8)
        q[name + "_s"] = np.float32(s)
    for idx, name in ((1, "b1"), (3, "b2"), (5, "b3")):
        q[name] = w[idx].astype(np.float32)
    return q


ACT_S = np.float32(1.0 / 127.0)      # activations live in [-1, 1] after tanh


def nn_int8(q, z):
    """Integer-arithmetic inference: exactly what firmware/05 executes."""
    xin = np.clip(np.round((z / SCALE) / ACT_S), -127, 127).astype(np.int32)

    acc = q["w1"].astype(np.int32) @ xin
    h = np.tanh(acc.astype(np.float32) * (q["w1_s"] * ACT_S) + q["b1"])
    hq = np.clip(np.round(h / ACT_S), -127, 127).astype(np.int32)

    acc = q["w2"].astype(np.int32) @ hq
    h = np.tanh(acc.astype(np.float32) * (q["w2_s"] * ACT_S) + q["b2"])
    hq = np.clip(np.round(h / ACT_S), -127, 127).astype(np.int32)

    acc = q["w3"].astype(np.int32) @ hq
    out = acc.astype(np.float32) * (q["w3_s"] * ACT_S) + q["b3"]
    return float(out[0]) * U_SCALE


# =============================================================================
# 5. closed-loop runs and metrics
# =============================================================================
# --- sensor model -----------------------------------------------------------
# The controller never sees the true gap. It sees the differential Hall
# signal through a 12-bit ADC after 16x oversampling. Both numbers below are
# DESIGN ASSUMPTIONS to be replaced by protocol P3 measurements:
SENSOR_SIGMA = 4.0e-6      # m, RMS noise of the position estimate
SENSOR_LSB = 2.0e-6        # m, quantisation step of the position estimate
TAU_D = 2.0e-3             # s, first-order filter on the derivative channel


# --- current observer --------------------------------------------------------
# The controller does not receive the true coil current either. The INA219
# needs ~0.5 ms per I2C transaction against a 1 ms control period, so the
# firmware estimates the current from the commanded duty through the coil time
# constant. The simulation MUST use the same estimate: feeding it the true
# current would hand the network information the hardware cannot provide, and
# the resulting figures would be optimistic by an unknown margin.
#
# Симуляция обязана использовать ту же оценку: подача истинного тока дала бы
# сети информацию, которой на железе нет, и числа оказались бы завышенными.
ALPHA_E = TS / (P.tau_electrical + TS)
I_MAX = P.U_supply / P.R_coil


def run(ctrl, t_end=2.0, kick=0.05, t_kick=0.5, x_init=None, seed=0):
    """Simulate; apply a reproducible velocity impulse at t_kick."""
    noise = np.random.default_rng(seed)
    s = np.array([P.x0 if x_init is None else x_init, 0.0, P.i0])
    n = int(t_end / TS)
    log = np.zeros((n, 5))
    alpha = TS / (TAU_D + TS)
    e_prev = s[0] - P.x0
    de_f = 0.0
    i_est = P.i0                     # observer state, same seed value as fw
    for t in range(n):
        e_true = s[0] - P.x0
        e = SENSOR_LSB * round((e_true + noise.normal(0.0, SENSOR_SIGMA)) / SENSOR_LSB)
        de_f += alpha * ((e - e_prev) / TS - de_f)
        e_prev = e
        duty = ctrl(e, de_f, i_est)
        log[t] = (t * TS, s[0], s[2], duty, i_est)
        # observer updated after the command is issued, exactly as in firmware
        i_est += ALPHA_E * (duty * I_MAX - i_est)
        s = step(s, duty)
        if abs(t * TS - t_kick) < TS / 2:
            s[1] += kick
        if not np.isfinite(s).all() or s[0] > 12e-3 or s[0] < 0.25e-3:
            return log[:t + 1], False
    return log, True


def metrics(log, ok):
    if not ok:
        return dict(stable=False, rms_um=float("nan"), settling_ms=float("nan"))
    t, x = log[:, 0], log[:, 1]
    steady = (t > 0.20) & (t < 0.49)
    rms = float(np.sqrt(np.mean((x[steady] - P.x0) ** 2)) * 1e6)   # µm
    band = 50e-6      # 2 % of the working gap
    after = t >= 0.5
    err = np.abs(x[after] - P.x0)
    ta = t[after]
    settle = float("nan")
    for j in range(len(err)):
        if np.all(err[j:] < band):
            settle = (ta[j] - 0.5) * 1e3
            break
    return dict(stable=True, rms_um=rms, settling_ms=settle)


def capture_range(ctrl):
    """Largest initial gap offset from which the loop still recovers, mm."""
    lo, hi = 0.0, 2.5e-3
    for _ in range(13):
        mid = 0.5 * (lo + hi)
        _, ok = run(ctrl, t_end=0.8, kick=0.0, t_kick=9.9, x_init=P.x0 + mid)
        lo, hi = (mid, hi) if ok else (lo, mid)
    return lo * 1e3


# =============================================================================
def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(FIG, exist_ok=True)
    print("building MPC dataset ...")
    X, y = build_dataset()
    print("training MLP 3-16-16-1 ...")
    w, final_loss = train_mlp(X, y)
    q = quantise(w)

    pred_f = np.array([nn_float(w, z) for z in X])
    pred_q = np.array([nn_int8(q, z) for z in X])
    open_loop = {
        "mae_float_duty": float(np.mean(np.abs(pred_f - y))),
        "mae_int8_duty": float(np.mean(np.abs(pred_q - y))),
        "max_int8_minus_float": float(np.max(np.abs(pred_q - pred_f))),
        "train_mse_normalised": final_loss,
    }

    controllers = {
        "PID": PID(),
        "MPC (float64, PC)": MPCController(),
        "NN float32": lambda e, de, i: float(np.clip(DUTY0 + nn_float(w, np.array([e, de, i - P.i0])), 0, 1)),
        "NN int8": lambda e, de, i: float(np.clip(DUTY0 + nn_int8(q, np.array([e, de, i - P.i0])), 0, 1)),
    }

    results, traces = {}, {}
    N_SEEDS = 8
    for name, c in controllers.items():
        print(f"running {name} ({N_SEEDS} noise realisations) ...")
        rms, settle = [], []
        for sd in range(N_SEEDS):
            if isinstance(c, PID):
                c.integ = 0.0
            log, ok = run(c, seed=sd)
            mm = metrics(log, ok)
            if mm["stable"]:
                rms.append(mm["rms_um"])
                if not math.isnan(mm["settling_ms"]):
                    settle.append(mm["settling_ms"])
            if sd == 0:
                traces[name] = log
        m = dict(stable=bool(rms),
                 rms_um=float(np.mean(rms)) if rms else float("nan"),
                 rms_sd=float(np.std(rms)) if rms else float("nan"),
                 settling_ms=float(np.mean(settle)) if settle else float("nan"),
                 settling_sd=float(np.std(settle)) if settle else float("nan"))
        m["capture_mm"] = capture_range(c)
        results[name] = m

    # --- memory and step-time estimates for the MCU --------------------------
    n_params = sum(a.size for a in w)
    macs = 3 * 16 + 16 * 16 + 16 * 1
    results["NN float32"]["bytes"] = n_params * 4
    results["NN int8"]["bytes"] = (q["w1"].size + q["w2"].size + q["w3"].size) + \
                                  (w[1].size + w[3].size + w[5].size) * 4
    results["NN float32"]["macs"] = macs
    results["NN int8"]["macs"] = macs

    with open(os.path.join(OUT, "simulation_summary.json"), "w") as f:
        json.dump({"plant": {k: float(v) for k, v in
                             dict(m_g=P.m * 1e3, x0_mm=P.x0 * 1e3, i0_A=P.i0,
                                  pole_rad_s=P.pole, tau_ms=P.tau_unstable * 1e3).items()},
                   "open_loop": open_loop, "closed_loop": results,
                   "n_params": n_params, "macs_per_step": macs}, f, indent=2)

    with open(os.path.join(OUT, "controller_comparison_sim.csv"), "w") as f:
        f.write("controller,rms_error_um,rms_sd_um,settling_ms,settling_sd_ms,"
                "capture_range_mm,params_bytes,macs\n")
        for name, m in results.items():
            f.write(f"{name},{m['rms_um']:.2f},{m['rms_sd']:.2f},{m['settling_ms']:.1f},"
                    f"{m['settling_sd']:.1f},{m['capture_mm']:.3f},"
                    f"{m.get('bytes', '')},{m.get('macs', '')}\n")

    np.savez(os.path.join(OUT, "traces.npz"), **{k.replace(" ", "_"): v for k, v in traces.items()})
    np.savez(os.path.join(HERE, "nn_weights.npz"),
             **{f"float_{i}": a for i, a in enumerate(w)},
             **{f"q_{k}": v for k, v in q.items()})

    print("\n" + "=" * 74)
    print(f"{'controller':<20}{'RMS, µm':>16}{'settling, ms':>16}"
          f"{'capture, mm':>13}{'bytes':>9}")
    print("-" * 78)
    for name, m in results.items():
        print(f"{name:<20}{m['rms_um']:>10.2f}±{m['rms_sd']:<5.2f}"
              f"{m['settling_ms']:>10.1f}±{m['settling_sd']:<5.1f}"
              f"{m['capture_mm']:>13.3f}{str(m.get('bytes', '—')):>9}")
    print("=" * 74)
    print(f"open-loop imitation error (duty units):  float32 {open_loop['mae_float_duty']:.5f}"
          f"   int8 {open_loop['mae_int8_duty']:.5f}")
    print(f"max |int8 − float32| over the dataset:   {open_loop['max_int8_minus_float']:.5f}")
    print(f"network: {n_params} parameters, {macs} MAC/step")


if __name__ == "__main__":
    main()
