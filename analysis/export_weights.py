#!/usr/bin/env python3
"""
Export the trained network into C headers for the firmware.
Экспорт обученной сети в заголовки C для прошивки.

Reads  analysis/nn_weights.npz  (written by simulate_controllers.py)
Writes firmware/05_nn_controller/nn_weights.h   (int8 tensors + scales)
       firmware/05_nn_controller/nn_float.h     (float32 reference)

The float32 header exists so the same board can run both arithmetics and
the comparison is apples to apples: same network, same inputs, same loop.
"""

import os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FW = os.path.join(HERE, "..", "firmware", "05_nn_controller")

SCALE = np.array([0.45e-3, 0.35, 0.12], dtype=np.float32)
U_SCALE = np.float32(0.5)

HDR = """/*
 * {name} — GENERATED FILE, DO NOT EDIT
 *          СГЕНЕРИРОВАННЫЙ ФАЙЛ, НЕ РЕДАКТИРОВАТЬ
 *
 * Produced by analysis/export_weights.py from the network trained in
 * analysis/simulate_controllers.py. Regenerate after any retraining:
 *     python3 analysis/simulate_controllers.py && python3 analysis/export_weights.py
 *
 * Network: 3-16-16-1, tanh hidden, trained to imitate a 40-step linear MPC.
 * {extra}
 */

#ifndef {guard}
#define {guard}

#include <stdint.h>

"""


def c_array_2d(name, arr, ctype):
    rows = []
    for r in arr:
        rows.append("  {" + ", ".join(f"{v:d}" if ctype == "int8_t" else f"{v:.8g}f"
                                      for v in r) + "}")
    return (f"static const {ctype} {name}[{arr.shape[0]}][{arr.shape[1]}] = {{\n"
            + ",\n".join(rows) + "\n};\n\n")


def c_array_1d(name, arr, ctype="float"):
    body = ", ".join(f"{v:.8g}f" for v in arr)
    return f"static const {ctype} {name}[{len(arr)}] = {{{body}}};\n\n"


def main():
    z = np.load(os.path.join(HERE, "nn_weights.npz"))
    w = [z[f"float_{i}"] for i in range(6)]

    # ---------------- int8 header ----------------------------------------
    out = HDR.format(name="nn_weights.h", guard="NN_WEIGHTS_H",
                     extra="Quantisation: symmetric per-tensor int8 weights, "
                           "float biases,\n * int32 accumulator, activations rescaled to int8 after each tanh.")
    out += "/* input scaling: x_normalised = x * NN_IN_INV_SCALE */\n"
    out += c_array_1d("NN_IN_INV_SCALE", 1.0 / SCALE)
    out += f"#define NN_OUT_SCALE {float(U_SCALE):.8g}f\n\n"

    total_int8 = 0
    for idx, wn, sn in ((0, "NN_W1", "NN_W1_SCALE"),
                        (2, "NN_W2", "NN_W2_SCALE"),
                        (4, "NN_W3", "NN_W3_SCALE")):
        W = w[idx]
        s = float(np.max(np.abs(W)) / 127.0)
        Wq = np.clip(np.round(W / s), -127, 127).astype(np.int8)
        out += f"#define {sn} {s:.8g}f\n"
        out += c_array_2d(wn, Wq, "int8_t")
        total_int8 += Wq.size

    for idx, bn in ((1, "NN_B1"), (3, "NN_B2"), (5, "NN_B3")):
        out += c_array_1d(bn, w[idx])

    n_bias = w[1].size + w[3].size + w[5].size
    out += (f"/* footprint: {total_int8} int8 weights + {n_bias} float biases"
            f" = {total_int8 + n_bias * 4} bytes */\n\n#endif\n")
    with open(os.path.join(FW, "nn_weights.h"), "w") as f:
        f.write(out)

    # ---------------- float32 reference header ---------------------------
    out = HDR.format(name="nn_float.h", guard="NN_FLOAT_H",
                     extra="Float32 reference implementation, used as the "
                           "baseline row of the\n * comparison table.")
    out += "#include <math.h>\n#include \"nn_weights.h\"\n\n"
    for idx, wn in ((0, "NNF_W1"), (2, "NNF_W2"), (4, "NNF_W3")):
        out += c_array_2d(wn, w[idx], "float")
    out += """static inline float nn_float_forward(const float in[3]) {
  float h1[16], h2[16];
  for (int j = 0; j < 16; j++) {
    float a = NN_B1[j];
    for (int i = 0; i < 3; i++) a += NNF_W1[j][i] * in[i] * NN_IN_INV_SCALE[i];
    h1[j] = tanhf(a);
  }
  for (int j = 0; j < 16; j++) {
    float a = NN_B2[j];
    for (int i = 0; i < 16; i++) a += NNF_W2[j][i] * h1[i];
    h2[j] = tanhf(a);
  }
  float a = NN_B3[0];
  for (int i = 0; i < 16; i++) a += NNF_W3[0][i] * h2[i];
  return a * NN_OUT_SCALE;
}

"""
    n_float = sum(a.size for a in w)
    out += f"/* footprint: {n_float} float32 parameters = {n_float * 4} bytes */\n\n#endif\n"
    with open(os.path.join(FW, "nn_float.h"), "w") as f:
        f.write(out)

    print(f"wrote nn_weights.h ({total_int8 + n_bias * 4} B) and "
          f"nn_float.h ({n_float * 4} B)")


if __name__ == "__main__":
    main()
