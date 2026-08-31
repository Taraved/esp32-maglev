/*
 * 05_nn_controller — int8 neural controller, the measurement this project exists for
 *                    нейроконтроллер int8 — ради этого измерения проект и делается
 *
 * The network imitates an MPC that cannot run on the MCU (the MPC solves a
 * 40-step QP; measured at ~40 ms per step on a PC). The network reproduces its
 * policy in a few hundred microseconds, and the question is how much control
 * quality is lost when its arithmetic drops from float32 to int8 on a plant
 * that amplifies every error.
 *
 * Сеть имитирует MPC, который не помещается в микроконтроллер. Вопрос: сколько
 * качества управления теряется при переходе float32 -> int8 на объекте,
 * который усиливает любую ошибку.
 *
 * MODE selects which controller drives the coil, so the same binary produces
 * all four rows of the comparison table without changing anything else.
 */

#include "nn_int8.h"
#include "nn_float.h"

#define MODE_PID     0
#define MODE_NN_F32  1
#define MODE_NN_INT8 2

#ifndef MODE
#define MODE MODE_NN_INT8
#endif

constexpr int PIN_HALL_A = 4;
constexpr int PIN_HALL_B = 5;
constexpr int PIN_PWM    = 16;
constexpr int PIN_PROBE  = 17;

constexpr int   PWM_BITS   = 11;
constexpr int   DUTY_MAX   = (1 << PWM_BITS) - 1;
constexpr float TS         = 1e-3f;
constexpr float TAU_D      = 2e-3f;
constexpr float ALPHA_D    = TS / (TAU_D + TS);
constexpr float DUTY_BIAS  = 0.5625f;    // = i0 * R / U at the design point
constexpr float SETPOINT_M = 2.5e-3f;

/* coil current observer: the INA219 needs 0.5 ms per reading, far too slow
 * for the loop, so the current is estimated from the duty through the coil
 * time constant. tau_e = L/R = 1.48 ms by design; replace with the measured
 * value from protocol P2. */
constexpr float TAU_E   = 1.48e-3f;
constexpr float ALPHA_E = TS / (TAU_E + TS);
constexpr float I_MAX   = 12.0f / 27.0f;

/* calibration placeholders, filled from data/calibration/ after protocol P3 */
constexpr float CAL_C0 = 2.50e-3f, CAL_C1 = -1.00e-6f, CAL_C2 = 0.0f;

static float i_est = 0.25f;

static inline float gapFromDiff(int d) {
  const float x = (float)d;
  return CAL_C0 + CAL_C1 * x + CAL_C2 * x * x;
}

void controlTask(void *) {
  TickType_t last = xTaskGetTickCount();
  float e_prev = 0.0f, de_f = 0.0f, integ = 0.0f;
  uint32_t worst_us = 0;

  for (;;) {
    const uint32_t t0 = micros();
    digitalWrite(PIN_PROBE, HIGH);

    long sa = 0, sb = 0;
    for (int k = 0; k < 8; k++) { sa += analogRead(PIN_HALL_A); sb += analogRead(PIN_HALL_B); }
    const float gap = gapFromDiff((int)((sa - sb) / 8));

    const float e = gap - SETPOINT_M;
    de_f += ALPHA_D * ((e - e_prev) / TS - de_f);
    e_prev = e;

    float duty;
#if MODE == MODE_PID
    integ = constrain(integ + e * TS, -2e-3f, 2e-3f);
    duty = DUTY_BIAS + 400.0f * e + 4.0f * de_f + 400.0f * integ;
#else
    const float in[3] = { e, de_f, i_est - 0.25f };
  #if MODE == MODE_NN_F32
    duty = DUTY_BIAS + nn_float_forward(in);
  #else
    duty = DUTY_BIAS + nn_int8_forward(in);
  #endif
#endif
    duty = constrain(duty, 0.0f, 1.0f);
    ledcWrite(PIN_PWM, (int)(duty * DUTY_MAX));

    /* first-order current observer, updated after the command is issued */
    i_est += ALPHA_E * (duty * I_MAX - i_est);

    digitalWrite(PIN_PROBE, LOW);
    const uint32_t dt = micros() - t0;
    if (dt > worst_us) {
      worst_us = dt;
      Serial.printf("worst step: %u us\n", worst_us);   /* core 0, rare */
    }
    vTaskDelayUntil(&last, pdMS_TO_TICKS(1));
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_PROBE, OUTPUT);
  analogReadResolution(12);
  analogSetPinAttenuation(PIN_HALL_A, ADC_11db);
  analogSetPinAttenuation(PIN_HALL_B, ADC_11db);
  ledcAttach(PIN_PWM, 20000, PWM_BITS);
  ledcWrite(PIN_PWM, 0);

  Serial.printf("mode %d, %d MACs/step\n", MODE, NN_MACS);
  xTaskCreatePinnedToCore(controlTask, "ctrl", 4096, nullptr, 20, nullptr, 0);
}

void loop() { delay(1000); }
