/*
 * 01_pwm_test — power stage bring-up / проверка силового ключа
 *
 * Purpose: verify that the MOSFET switches the coil and that the flyback
 * diode clamps the drain, BEFORE any sensor or control code exists.
 * Назначение: убедиться, что ключ коммутирует катушку и диод гасит выброс,
 * ДО того как появится хоть строчка кода регулятора.
 *
 * Board: ESP32-S3-DevKitC-1 (ESP32-S3-WROOM-1 N16R8)
 * Arduino-ESP32 core 3.x. For core 2.x see the note at ledcAttach().
 *
 * Expected on the oscilloscope at the drain:
 *   - clean 20 kHz square wave
 *   - turn-off overshoot below 15-20 V  (higher => diode problem)
 *
 * SAFETY: run this first at 5 V, not 12 V. The coil draws 0.2 A at 5 V,
 * which any USB charger survives, and a wiring error costs nothing.
 */

constexpr int PIN_PWM = 16;      // -> 100 ohm -> IRLZ44N gate
constexpr int PWM_FREQ = 20000;  // Hz: above the audible range
constexpr int PWM_BITS = 11;     // 0..2047
constexpr int DUTY_MAX = (1 << PWM_BITS) - 1;

void setup() {
  Serial.begin(115200);
  delay(300);

  // core 3.x:
  ledcAttach(PIN_PWM, PWM_FREQ, PWM_BITS);
  // core 2.x equivalent:
  //   ledcSetup(0, PWM_FREQ, PWM_BITS);
  //   ledcAttachPin(PIN_PWM, 0);
  //   ledcWrite(0, duty);

  ledcWrite(PIN_PWM, 0);
  Serial.printf("PWM %d Hz, %d bit, max duty %d\n", PWM_FREQ, PWM_BITS, DUTY_MAX);
  Serial.println("ramping up and down; the coil must attract at high duty");
}

void loop() {
  for (int d = 0; d <= DUTY_MAX; d += 32) {
    ledcWrite(PIN_PWM, d);
    delay(20);
  }
  Serial.println("full on");
  delay(500);
  for (int d = DUTY_MAX; d >= 0; d -= 32) {
    ledcWrite(PIN_PWM, d);
    delay(20);
  }
  Serial.println("off");
  delay(1000);
}
