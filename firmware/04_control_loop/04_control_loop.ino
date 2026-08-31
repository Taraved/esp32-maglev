/*
 * 04_control_loop — 1 kHz PID levitation controller with Wi-Fi telemetry
 *                   контур левитации 1 кГц с телеметрией по Wi-Fi
 *
 * Architecture / архитектура:
 *   Core 0 : hard real-time control task, 1 ms period, highest priority.
 *   Core 1 : Wi-Fi access point, web UI, telemetry. Never touches the loop.
 *
 * The split matters. On a single-core MCU the Wi-Fi stack would steal the
 * control tick and the ball would drop; here the loop cannot be preempted.
 * Разделение принципиально: на одноядерном контроллере стек Wi-Fi сорвал бы
 * такт регулятора и шарик упал бы.
 *
 * Board: ESP32-S3-DevKitC-1 (N16R8), Arduino-ESP32 core 3.x
 *
 * Pins  GPIO 4  Hall A (ADC1_CH3)      GPIO 16  PWM -> 100 ohm -> gate
 *       GPIO 5  Hall B (ADC1_CH4)      GPIO 17  timing probe (scope)
 *
 * Web UI: connect to the AP "maglev" (password "levitate"), open 192.168.4.1
 * Kp/Ki/Kd and the setpoint are editable live: retuning drops from a
 * 2-3 minute edit-compile-flash cycle to a 2 second field edit.
 */

#include <WiFi.h>
#include <WebServer.h>

// ---------------------------------------------------------------- pins ----
constexpr int PIN_HALL_A = 4;
constexpr int PIN_HALL_B = 5;
constexpr int PIN_PWM    = 16;
constexpr int PIN_PROBE  = 17;

// ------------------------------------------------------------ constants ---
constexpr int   PWM_FREQ    = 20000;
constexpr int   PWM_BITS    = 11;
constexpr int   DUTY_MAX    = (1 << PWM_BITS) - 1;
constexpr int   OVERSAMPLE  = 8;        // 8 x 12 bit -> ~13.5 effective bits
constexpr float LOOP_HZ     = 1000.0f;
constexpr float TS          = 1.0f / LOOP_HZ;

// Derivative low-pass. A pure difference of a noisy signal is unusable, but
// filtering costs phase, and phase on an unstable plant costs stability.
// tau = 2 ms is the compromise measured in simulation (analysis/).
constexpr float TAU_D       = 0.002f;
constexpr float ALPHA_D     = TS / (TAU_D + TS);

// Safety: if the position signal leaves the working window for longer than
// this, the ball is gone (or was never there) and the coil must be cut.
// Without this the coil sits at full current and cooks itself.
constexpr float GAP_MIN_MM  = 0.8f;
constexpr float GAP_MAX_MM  = 6.0f;
constexpr int   LOST_TICKS  = 50;       // 50 ms

// ---------------------------------------------------- calibration ---------
// Position from the differential Hall signal:  gap_mm = C0 + C1*d + C2*d^2
// d = (raw_a - raw_b), in ADC counts.
// THESE ARE PLACEHOLDERS. They are filled from data/calibration/ after
// protocol P3 is run; see docs/03-measurement-protocol.
// ЭТО ЗАГЛУШКИ, заполняются по результатам протокола P3.
volatile float CAL_C0 = 2.50f;
volatile float CAL_C1 = -1.00e-3f;
volatile float CAL_C2 = 0.0f;

// ------------------------------------------------------- shared state -----
struct Gains { float kp, ki, kd, setpoint_mm; };
volatile Gains g = { 400.0f * 1e-3f, 400.0f * 1e-3f, 4.0f * 1e-3f, 2.50f };
// note: the simulation works in metres, the firmware in millimetres, hence
// the 1e-3 factors above. Keeping the firmware in mm makes the web UI
// readable and avoids float underflow in the integrator.

struct Telemetry {
  float gap_mm, error_mm, duty, integ;
  uint32_t step_us, ticks, lost_events;
  bool levitating;
};
volatile Telemetry tel = {};

portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;
WebServer server(80);

// ------------------------------------------------------------ helpers -----
static inline int readPair(int &a, int &b) {
  long sa = 0, sb = 0;
  for (int i = 0; i < OVERSAMPLE; i++) {
    sa += analogRead(PIN_HALL_A);
    sb += analogRead(PIN_HALL_B);
  }
  a = static_cast<int>(sa / OVERSAMPLE);
  b = static_cast<int>(sb / OVERSAMPLE);
  return a - b;
}

static inline float diffToGapMm(int d) {
  const float x = static_cast<float>(d);
  return CAL_C0 + CAL_C1 * x + CAL_C2 * x * x;
}

// ------------------------------------------------- control task (core 0) --
void controlTask(void *) {
  TickType_t last = xTaskGetTickCount();
  float integ = 0.0f, e_prev = 0.0f, de_f = 0.0f;
  int lost = 0;
  uint32_t ticks = 0, lost_events = 0;

  for (;;) {
    const uint32_t t0 = micros();
    digitalWrite(PIN_PROBE, HIGH);     // rising edge = start of the step

    int ra, rb;
    const int d = readPair(ra, rb);
    const float gap = diffToGapMm(d);

    Gains gain;
    portENTER_CRITICAL(&mux);
    gain = const_cast<Gains &>(g);
    portEXIT_CRITICAL(&mux);

    const float e = gap - gain.setpoint_mm;
    de_f += ALPHA_D * ((e - e_prev) / TS - de_f);
    e_prev = e;

    bool inRange = (gap > GAP_MIN_MM) && (gap < GAP_MAX_MM);
    lost = inRange ? 0 : lost + 1;

    float duty_f = 0.0f;
    if (lost < LOST_TICKS) {
      integ += e * TS;
      integ = constrain(integ, -0.5f, 0.5f);          // anti-windup
      duty_f = 0.5625f                                 // bias at equilibrium
             + gain.kp * e
             + gain.kd * de_f
             + gain.ki * integ;
      duty_f = constrain(duty_f, 0.0f, 1.0f);
    } else {
      integ = 0.0f;                                    // object lost: coil off
      if (lost == LOST_TICKS) lost_events++;
    }

    ledcWrite(PIN_PWM, static_cast<int>(duty_f * DUTY_MAX));
    digitalWrite(PIN_PROBE, LOW);      // falling edge = end of the step

    ticks++;
    portENTER_CRITICAL(&mux);
    tel.gap_mm = gap;
    tel.error_mm = e;
    tel.duty = duty_f;
    tel.integ = integ;
    tel.step_us = micros() - t0;
    tel.ticks = ticks;
    tel.lost_events = lost_events;
    tel.levitating = (lost < LOST_TICKS);
    portEXIT_CRITICAL(&mux);

    vTaskDelayUntil(&last, pdMS_TO_TICKS(1));          // exactly 1 kHz
  }
}

// ------------------------------------------------------- web UI (core 1) --
const char PAGE[] PROGMEM = R"HTML(<!doctype html><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>maglev</title><style>
body{font:15px system-ui;margin:0;background:#0b0f19;color:#e8edf7;padding:16px}
h1{font-size:18px;margin:0 0 12px}
canvas{width:100%;height:180px;background:#131b2e;border-radius:8px}
label{display:block;margin:10px 0 3px;color:#94a3b8;font-size:13px}
input{width:100%;padding:7px;background:#0f1626;color:#e8edf7;
border:1px solid #233554;border-radius:6px;font:inherit}
button{margin-top:12px;padding:9px 16px;background:#38bdf8;color:#08111f;
border:0;border-radius:7px;font:inherit;font-weight:600}
.s{display:flex;gap:14px;margin:12px 0;flex-wrap:wrap}
.s div{background:#131b2e;padding:8px 12px;border-radius:7px;font-size:13px}
b{color:#38bdf8}</style>
<h1>Maglev &mdash; live</h1><canvas id=c></canvas>
<div class=s><div>gap <b id=g>-</b> mm</div><div>duty <b id=d>-</b></div>
<div>step <b id=t>-</b> &micro;s</div><div>state <b id=st>-</b></div></div>
<label>Kp</label><input id=kp><label>Ki</label><input id=ki>
<label>Kd</label><input id=kd><label>setpoint, mm</label><input id=sp>
<button onclick=send()>apply</button>
<script>
const c=document.getElementById('c'),x=c.getContext('2d'),buf=[];
function draw(){c.width=c.clientWidth;c.height=180;x.clearRect(0,0,c.width,180);
x.strokeStyle='#334155';x.beginPath();x.moveTo(0,90);x.lineTo(c.width,90);x.stroke();
x.strokeStyle='#38bdf8';x.beginPath();
buf.forEach((v,i)=>{const y=90-v*400;i?x.lineTo(i*c.width/300,y):x.moveTo(0,y)});x.stroke()}
async function poll(){try{const r=await(await fetch('/t')).json();
document.getElementById('g').textContent=r.gap.toFixed(3);
document.getElementById('d').textContent=r.duty.toFixed(3);
document.getElementById('t').textContent=r.step;
document.getElementById('st').textContent=r.lev?'levitating':'idle';
buf.push(r.err);if(buf.length>300)buf.shift();draw()}catch(e){}}
setInterval(poll,50);
async function send(){const q=new URLSearchParams({kp:kp.value,ki:ki.value,
kd:kd.value,sp:sp.value});await fetch('/set?'+q)}
fetch('/t').then(r=>r.json()).then(r=>{kp.value=r.kp;ki.value=r.ki;
kd.value=r.kd;sp.value=r.sp});
</script>)HTML";

void handleTelemetry() {
  Telemetry t;
  Gains gg;
  portENTER_CRITICAL(&mux);
  t = const_cast<Telemetry &>(tel);
  gg = const_cast<Gains &>(g);
  portEXIT_CRITICAL(&mux);

  char buf[320];
  snprintf(buf, sizeof(buf),
           "{\"gap\":%.4f,\"err\":%.4f,\"duty\":%.4f,\"step\":%u,\"ticks\":%u,"
           "\"lost\":%u,\"lev\":%s,\"kp\":%.4f,\"ki\":%.4f,\"kd\":%.4f,\"sp\":%.3f}",
           t.gap_mm, t.error_mm, t.duty, t.step_us, t.ticks, t.lost_events,
           t.levitating ? "true" : "false", gg.kp, gg.ki, gg.kd, gg.setpoint_mm);
  server.send(200, "application/json", buf);
}

void handleSet() {
  Gains n;
  portENTER_CRITICAL(&mux);
  n = const_cast<Gains &>(g);
  portEXIT_CRITICAL(&mux);

  if (server.hasArg("kp")) n.kp = server.arg("kp").toFloat();
  if (server.hasArg("ki")) n.ki = server.arg("ki").toFloat();
  if (server.hasArg("kd")) n.kd = server.arg("kd").toFloat();
  if (server.hasArg("sp")) n.setpoint_mm = server.arg("sp").toFloat();

  portENTER_CRITICAL(&mux);
  g = n;
  portEXIT_CRITICAL(&mux);
  server.send(200, "text/plain", "ok");
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_PROBE, OUTPUT);

  analogReadResolution(12);
  analogSetPinAttenuation(PIN_HALL_A, ADC_11db);
  analogSetPinAttenuation(PIN_HALL_B, ADC_11db);

  ledcAttach(PIN_PWM, PWM_FREQ, PWM_BITS);
  ledcWrite(PIN_PWM, 0);

  // control task first, so a slow Wi-Fi bring-up cannot delay it
  xTaskCreatePinnedToCore(controlTask, "ctrl", 4096, nullptr, 20, nullptr, 0);

  WiFi.mode(WIFI_AP);
  WiFi.softAP("maglev", "levitate");
  server.on("/", []() { server.send_P(200, "text/html", PAGE); });
  server.on("/t", handleTelemetry);
  server.on("/set", handleSet);
  server.begin();
  Serial.printf("AP up: http://%s\n", WiFi.softAPIP().toString().c_str());
}

void loop() {
  server.handleClient();     // core 1 only
}
