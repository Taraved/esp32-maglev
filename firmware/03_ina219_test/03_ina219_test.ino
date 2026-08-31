/*
 * 03_ina219_test — coil current logging / логирование тока катушки
 *
 * The INA219 sits in the +12 V line (high-side, 0.1 ohm shunt) and is used
 * for plant identification and logging ONLY. One I2C transaction costs about
 * 0.5 ms, which is half of the 1 ms control period, so it must never be
 * called from inside the control loop.
 *
 * INA219 стоит в разрыве +12 В и используется только для идентификации
 * модели и логирования. Одна транзакция I2C занимает ~0.5 мс — половину
 * такта регулятора, поэтому внутри контура управления её вызывать нельзя.
 *
 * Pins: SDA = GPIO 8, SCL = GPIO 9 (the S3 defaults). Address 0x40.
 *
 * This sketch performs protocol P2: a duty staircase with the coil current
 * recorded at each step, which yields R_coil and, from the rise time, L_coil.
 */

#include <Wire.h>
#include <Adafruit_INA219.h>

constexpr int PIN_SDA = 8;
constexpr int PIN_SCL = 9;
constexpr int PIN_PWM = 16;

Adafruit_INA219 ina;

void setup() {
  Serial.begin(115200);
  delay(300);

  Wire.begin(PIN_SDA, PIN_SCL);
  if (!ina.begin()) {
    Serial.println("INA219 not found at 0x40 - check SDA/SCL and the GND wire");
    while (true) delay(1000);
  }
  ina.setCalibration_32V_1A();     // 1 A range: the coil draws ~0.45 A

  ledcAttach(PIN_PWM, 20000, 11);
  ledcWrite(PIN_PWM, 0);

  Serial.println("# protocol P2: duty staircase, coil R and L identification");
  Serial.println("# duty,duty_fraction,bus_v,shunt_mv,current_ma");
}

void loop() {
  for (int duty = 0; duty <= 2047; duty += 128) {
    ledcWrite(PIN_PWM, duty);
    delay(400);                               // >> L/R, so the current settles

    float i_ma = 0.0f, v_bus = 0.0f, v_sh = 0.0f;
    constexpr int N = 20;
    for (int k = 0; k < N; k++) {
      i_ma += ina.getCurrent_mA();
      v_bus += ina.getBusVoltage_V();
      v_sh += ina.getShuntVoltage_mV();
      delay(5);
    }
    Serial.printf("%d,%.4f,%.3f,%.3f,%.2f\n",
                  duty, duty / 2047.0f, v_bus / N, v_sh / N, i_ma / N);
  }
  ledcWrite(PIN_PWM, 0);
  Serial.println("# --- sweep complete, coil off for 30 s to cool ---");
  delay(30000);
}
