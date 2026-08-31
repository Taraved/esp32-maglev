/*
 * 02_hall_read — differential Hall pair, raw readout
 *                дифференциальная пара датчиков Холла, сырое чтение
 *
 * Purpose: find the sensor placement that maximises sensitivity to the ball
 * while minimising sensitivity to coil current, and record the calibration
 * table required by data/calibration/.
 *
 * Назначение: найти положение датчиков, где чувствительность к шарику
 * максимальна, а к току катушки минимальна, и снять калибровочную таблицу.
 *
 * Pins: GPIO 4 = Hall A (ADC1_CH3), GPIO 5 = Hall B (ADC1_CH4).
 * ADC1 is mandatory: ADC2 stops working once Wi-Fi is enabled.
 *
 * Output is CSV on the serial port so it can be piped straight into
 * analysis/fit_calibration.py:
 *     idf.py monitor | tee data/calibration/run_YYYYMMDD.csv
 */

constexpr int PIN_HALL_A = 4;
constexpr int PIN_HALL_B = 5;
constexpr int PIN_PWM = 16;
constexpr int OVERSAMPLE = 16;   // 16 samples -> +2 effective bits

// The coil is driven at a few fixed duty values so the common-mode rejection
// of the differential pair can be measured directly: sweep the duty with the
// ball absent, and dU must stay as flat as possible.
constexpr int DUTY_STEPS[] = {0, 256, 512, 1024};
constexpr int N_DUTY = sizeof(DUTY_STEPS) / sizeof(DUTY_STEPS[0]);

static inline int readAveraged(int pin) {
  long acc = 0;
  for (int i = 0; i < OVERSAMPLE; i++) acc += analogRead(pin);
  return static_cast<int>(acc / OVERSAMPLE);
}

void setup() {
  Serial.begin(115200);
  delay(300);

  analogReadResolution(12);                       // 0..4095
  analogSetPinAttenuation(PIN_HALL_A, ADC_11db);  // ~0..3.1 V
  analogSetPinAttenuation(PIN_HALL_B, ADC_11db);

  ledcAttach(PIN_PWM, 20000, 11);
  ledcWrite(PIN_PWM, 0);

  Serial.println("# duty,raw_a,raw_b,diff,volt_a,volt_b");
  Serial.println("# hold the ball at a known gap, then record one block per gap");
}

void loop() {
  for (int k = 0; k < N_DUTY; k++) {
    ledcWrite(PIN_PWM, DUTY_STEPS[k]);
    delay(200);                                   // let the coil current settle

    for (int n = 0; n < 25; n++) {
      int a = readAveraged(PIN_HALL_A);
      int b = readAveraged(PIN_HALL_B);
      Serial.printf("%d,%d,%d,%d,%.4f,%.4f\n",
                    DUTY_STEPS[k], a, b, a - b,
                    a * 3.1f / 4095.0f, b * 3.1f / 4095.0f);
      delay(20);
    }
  }
  ledcWrite(PIN_PWM, 0);
  Serial.println("# --- block end ---");
  delay(2000);
}
