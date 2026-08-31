# Firmware

Arduino-ESP32 core 3.x, board **ESP32-S3-DevKitC-1** (ESP32-S3-WROOM-1 N16R8).
For core 2.x the LEDC calls differ; the equivalent is noted in
`01_pwm_test/01_pwm_test.ino`.

The sketches are numbered in the order they must be run. Each one is a
self-contained bring-up step with its own acceptance criterion, because on an
unstable plant a system that fails all at once is impossible to debug.

| # | Sketch | Purpose | Acceptance |
|---|---|---|---|
| 01 | `01_pwm_test` | switch the coil, verify the flyback clamp | clean 20 kHz at the drain, turn-off overshoot < 15–20 V |
| 02 | `02_hall_read` | raw differential Hall readout, CSV to serial | `diff` monotone with gap; flat against duty with no ball |
| 03 | `03_ina219_test` | duty staircase, coil R and L | current linear in duty, `R²` > 0.99 |
| 04 | `04_control_loop` | 1 kHz PID + Wi-Fi web UI | ball held 10 min, settling time repeatable |
| 05 | `05_nn_controller` | float32 and int8 neural controller | all four rows of the comparison table |

## Pins

| Signal | Pin |
|---|---|
| Hall A / Hall B | GPIO 4 / GPIO 5 (ADC1) |
| PWM to gate | GPIO 16 |
| I²C SDA / SCL | GPIO 8 / GPIO 9 |
| Step-time probe | GPIO 17 |

**Never** use GPIO 35/36/37 (octal PSRAM), 19/20 (USB), 0/3/45/46 (strapping),
or ADC2 (GPIO 11–20) for analogue input with Wi-Fi enabled.

## Web interface

`04_control_loop` brings up an access point `maglev` / `levitate`; the UI is at
`192.168.4.1`. Kp, Ki, Kd and the setpoint are editable live.

This is the least glamorous and most valuable part of the firmware: it turns a
tuning iteration from *edit → compile → flash → observe* (2–3 minutes) into
typing a number (2 seconds). Over an evening that is the difference between
twenty experiments and two hundred.

## Neural controller

`05_nn_controller` runs the same 3-16-16-1 network in two arithmetics,
selected by `-DMODE=`:

| MODE | Controller | Footprint |
|---|---|---|
| `MODE_PID` | reference PID | — |
| `MODE_NN_F32` | float32 network | 1412 B |
| `MODE_NN_INT8` | int8 network | 452 B |

`nn_weights.h` and `nn_float.h` are **generated**:

```bash
python3 analysis/simulate_controllers.py   # trains and quantises
python3 analysis/export_weights.py         # writes both headers
```

The int8 inference in `nn_int8.h` is written by hand — 320 MACs, int32
accumulator, symmetric per-tensor scales. A framework would add tens of
kilobytes of runtime, hide the step time behind an interpreter, and obscure
the quantisation scheme, which is the object of study.

`i_est` is a first-order observer of the coil current, not a measurement: the
INA219 needs 0.5 ms per reading against a 1 ms control period. Its time
constant comes from protocol P2.

## Calibration constants

`CAL_C0..CAL_C2` in sketches 04 and 05 are **placeholders**. They are filled
from `analysis/fit_calibration.py` after protocol P3 is run. Until then the
position readout is not physical.

---

## Flashing: what to install and in what order

Nothing here needs an IDE project file — each folder is a plain Arduino sketch.

### 1. Board support

Arduino IDE → Preferences → Additional board manager URLs:

```
https://espressif.github.io/arduino-esp32/package_esp32_index.json
```

then Tools → Board Manager → install **esp32 by Espressif Systems** (3.x).

Command line alternative:

```bash
arduino-cli core update-index --additional-urls \
  https://espressif.github.io/arduino-esp32/package_esp32_index.json
arduino-cli core install esp32:esp32 --additional-urls \
  https://espressif.github.io/arduino-esp32/package_esp32_index.json
```

### 2. Board settings

| Setting | Value | Why |
|---|---|---|
| Board | **ESP32S3 Dev Module** | not "ESP32 Dev Module" — different chip |
| Flash Size | 16 MB (128 Mb) | N16R8 |
| PSRAM | **OPI PSRAM** | the R8 half of N16R8; wrong setting → boot loop |
| Partition Scheme | Default 4 MB with spiffs | anything with ≥1.2 MB app |
| Upload Speed | 921600 | drop to 115200 if uploads fail |
| USB CDC On Boot | Enabled | so `Serial` reaches the USB-C port |

The board has **two USB-C sockets**: one is the native USB of the S3, the
other goes through the UART bridge. If the port does not appear, try the other
socket. If it still does not, hold **BOOT**, tap **RST**, release BOOT — that
forces the download mode.

### 3. Library

Only sketch 03 needs one: **Adafruit INA219** (Library Manager), which pulls
in Adafruit BusIO.

### 4. Upload

```bash
arduino-cli compile --fqbn esp32:esp32:esp32s3:PSRAM=opi,FlashSize=16M \
  firmware/01_pwm_test
arduino-cli upload  --fqbn esp32:esp32:esp32s3:PSRAM=opi,FlashSize=16M \
  -p /dev/cu.usbmodem* firmware/01_pwm_test
```

For sketch 05, select the arithmetic at compile time:

```bash
arduino-cli compile --fqbn esp32:esp32:esp32s3:PSRAM=opi,FlashSize=16M \
  --build-property "build.extra_flags=-DMODE=2" firmware/05_nn_controller
```

`MODE=0` PID · `MODE=1` float32 network · `MODE=2` int8 network.

### 5. Before the first upload with 12 V connected

Run the pre-power checks in the build documentation first, and start sketch 01
with the coil on **5 V**, not 12 V. A wiring error at 5 V costs nothing; at
12 V it costs the only IRLZ44N in the drawer.

## Safety interlock

Sketch 04 cuts the PWM if the position estimate leaves the 0.8–6.0 mm window
for 50 consecutive ticks. Do not remove it while debugging: without it the
coil sits at full current whenever the ball is absent, which is both a thermal
hazard and the fastest way to mistake a dropped ball for a tuning problem.
