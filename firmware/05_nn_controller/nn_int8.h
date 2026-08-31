/*
 * nn_int8.h — hand-written int8 inference for a 3-16-16-1 MLP
 *             целочисленный инференс сети 3-16-16-1, написан вручную
 *
 * Why by hand and not TFLite Micro:
 *   - 353 parameters do not justify a framework and its 50+ kB of runtime;
 *   - the step time must be bounded and measurable, which a hand-written
 *     loop makes trivial and an interpreter makes opaque;
 *   - the quantisation scheme is the object of study, so it must be visible.
 *
 * Почему вручную, а не TFLite Micro: 353 параметра не оправдывают фреймворк;
 * время шага должно быть детерминированным и измеримым; схема квантования —
 * сам предмет исследования, она должна быть на виду.
 *
 * Quantisation: symmetric per-tensor for weights, int32 accumulator,
 * activations rescaled to int8 after each tanh. Biases stay float: there are
 * only 33 of them and they cost nothing.
 *
 * Generated companion file nn_weights.h is produced by
 *     analysis/export_weights.py
 */

#ifndef NN_INT8_H
#define NN_INT8_H

#include <stdint.h>
#include <math.h>

#include "nn_weights.h"   // NN_W1, NN_W2, NN_W3, NN_B*, NN_*_SCALE, NN_IN_SCALE...

#define NN_IN   3
#define NN_H    16
#define NN_OUT  1

/* activations live in [-1, 1] after tanh, so one LSB is 1/127 */
#define NN_ACT_SCALE (1.0f / 127.0f)

static inline int8_t nn_saturate(float v) {
  const float q = roundf(v);
  if (q > 127.0f) return 127;
  if (q < -127.0f) return -127;
  return (int8_t)q;
}

/*
 * Returns the duty deviation from the equilibrium bias.
 * in[0] = gap error [m], in[1] = error rate [m/s], in[2] = current dev [A]
 */
static inline float nn_int8_forward(const float in[NN_IN]) {
  int8_t x[NN_IN];
  int8_t h1[NN_H];
  int8_t h2[NN_H];

  /* --- input quantisation: fixed scales, no division on the MCU --------- */
  for (int i = 0; i < NN_IN; i++) {
    x[i] = nn_saturate((in[i] * NN_IN_INV_SCALE[i]) / NN_ACT_SCALE);
  }

  /* --- layer 1: int8 x int8 -> int32 ------------------------------------ */
  for (int j = 0; j < NN_H; j++) {
    int32_t acc = 0;
    for (int i = 0; i < NN_IN; i++) {
      acc += (int32_t)NN_W1[j][i] * (int32_t)x[i];
    }
    const float y = (float)acc * (NN_W1_SCALE * NN_ACT_SCALE) + NN_B1[j];
    h1[j] = nn_saturate(tanhf(y) / NN_ACT_SCALE);
  }

  /* --- layer 2 ---------------------------------------------------------- */
  for (int j = 0; j < NN_H; j++) {
    int32_t acc = 0;
    for (int i = 0; i < NN_H; i++) {
      acc += (int32_t)NN_W2[j][i] * (int32_t)h1[i];
    }
    const float y = (float)acc * (NN_W2_SCALE * NN_ACT_SCALE) + NN_B2[j];
    h2[j] = nn_saturate(tanhf(y) / NN_ACT_SCALE);
  }

  /* --- output layer ----------------------------------------------------- */
  int32_t acc = 0;
  for (int i = 0; i < NN_H; i++) {
    acc += (int32_t)NN_W3[0][i] * (int32_t)h2[i];
  }
  const float out = (float)acc * (NN_W3_SCALE * NN_ACT_SCALE) + NN_B3[0];

  return out * NN_OUT_SCALE;
}

/* MAC count per step, for the step-time budget in docs/03 */
#define NN_MACS (NN_IN * NN_H + NN_H * NN_H + NN_H * NN_OUT)

#endif /* NN_INT8_H */
