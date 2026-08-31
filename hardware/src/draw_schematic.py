#!/usr/bin/env python3
"""
Генератор монтажной схемы стенда магнитной левитации.

Один источник -> два файла:
    schematic.png  (300 dpi, для отчёта и печати)
    schematic.svg  (вектор, встраивается в schematic.html)

Плата: ESP32-S3-DevKitC-1 / YD-ESP32-S3 (ESP32-S3-WROOM-1 N16R8).
Распиновка отличается от классического ESP32 — см. README.md, раздел «Распиновка».

Запуск (окружение проекта):
    /Users/master/Projects/venv/bin/python3 draw_schematic.py
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# ----------------------------------------------------------------------------
# Палитра
# ----------------------------------------------------------------------------
BG        = "#0b0f19"
CARD      = "#131b2e"
CARD_DIM  = "#0f1626"
BORDER    = "#233554"
TXT       = "#f8fafc"
TXT_DIM   = "#94a3b8"
TXT_FAINT = "#64748b"

W_12V   = "#ef4444"   # силовая шина +12 В
W_DRAIN = "#f43f5e"   # сток MOSFET / минус катушки
W_5V    = "#f97316"   # +5 В (питание датчиков Холла)
W_3V3   = "#10b981"   # +3.3 В (логика INA219)
W_GND   = "#64748b"   # общая земля
W_PWM   = "#eab308"   # ШИМ на затвор
W_ADCA  = "#06b6d4"   # аналоговый вход A
W_ADCB  = "#3b82f6"   # аналоговый вход B
W_SDA   = "#a855f7"   # I2C SDA
W_SCL   = "#e2e8f0"   # I2C SCL
W_PROBE = "#22d3ee"   # метка времени для осциллографа

ACCENT  = "#38bdf8"
WARN    = "#fbbf24"

# ----------------------------------------------------------------------------
# Каркас
# ----------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(26, 15), dpi=300, facecolor=BG)
ax.set_facecolor(BG)
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.set_aspect(15 / 26 * 100 / 100)
ax.axis("off")
ax.margins(0)
fig.subplots_adjust(left=0, right=1, top=1, bottom=0)


def card(x, y, w, h, title="", subtitle="", bg=CARD, border=BORDER, tcol=TXT, z=2):
    ax.add_patch(patches.FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.25,rounding_size=0.5",
        facecolor=bg, edgecolor=border, linewidth=1.3, zorder=z))
    if title:
        ax.text(x + w / 2, y + h - 1.1, title, ha="center", va="top",
                fontsize=11, fontweight="bold", color=tcol, zorder=z + 1)
    if subtitle:
        ax.text(x + w / 2, y + h - 2.6, subtitle, ha="center", va="top",
                fontsize=7.5, color=TXT_DIM, zorder=z + 1)


def txt(x, y, s, size=7.5, col=TXT_DIM, ha="left", va="center", weight="normal", z=6):
    ax.text(x, y, s, fontsize=size, color=col, ha=ha, va=va, fontweight=weight, zorder=z)


def wire(points, color, lw=1.7, z=4, dot_ends=True):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    ax.plot(xs, ys, color=color, linewidth=lw, solid_capstyle="round",
            solid_joinstyle="round", zorder=z)
    if dot_ends:
        ax.plot([xs[0], xs[-1]], [ys[0], ys[-1]], "o", color=color,
                markersize=3.4, zorder=z + 1)


def tag(x, y, s, color, size=7.0, pad=0.28):
    ax.text(x, y, s, fontsize=size, color=color, ha="center", va="center",
            zorder=8, fontweight="bold",
            bbox=dict(boxstyle=f"round,pad={pad}", facecolor=BG,
                      edgecolor=color, linewidth=0.9))


def junction(x, y, color):
    ax.plot([x], [y], "o", color=color, markersize=4.6, zorder=7)


# ----------------------------------------------------------------------------
# Заголовок
# ----------------------------------------------------------------------------
ax.add_patch(patches.FancyBboxPatch(
    (2, 93.4), 96, 5.6, boxstyle="round,pad=0.3,rounding_size=0.7",
    facecolor=CARD, edgecolor=ACCENT, linewidth=1.5, zorder=2))
ax.text(50, 96.9, "МОНТАЖНАЯ СХЕМА СТЕНДА МАГНИТНОЙ ЛЕВИТАЦИИ",
        ha="center", va="center", fontsize=17, fontweight="bold", color=TXT, zorder=3)
ax.text(50, 94.7,
        "ESP32-S3-WROOM-1 N16R8  •  силовой ключ IRLZ44N + 1N5822  •  "
        "дифференциальная пара SS49E  •  токовый монитор INA219  •  рабочий зазор 2.5 мм",
        ha="center", va="center", fontsize=9.5, color=TXT_DIM, zorder=3)

# ============================================================================
# 1. ПЛАТА ESP32-S3
# ============================================================================
BX, BY, BW, BH = 3.0, 7.5, 20.0, 84.5
card(BX, BY, BW, BH, "ESP32-S3-DevKitC-1 (N16R8)",
     "16 МБ Flash • 8 МБ octal PSRAM • 2 × USB-C")

# модуль
ax.add_patch(patches.FancyBboxPatch(
    (BX + 5.4, BY + BH - 10.5), 9.2, 6.6, boxstyle="round,pad=0.2,rounding_size=0.3",
    facecolor="#1e293b", edgecolor="#475569", linewidth=1.0, zorder=3))
txt(BX + 10.0, BY + BH - 6.2, "ESP32-S3-WROOM-1", 7.2, TXT, ha="center", weight="bold", z=4)
txt(BX + 10.0, BY + BH - 7.5, "Xtensa LX7 dual-core 240 МГц", 6.0, TXT_DIM, ha="center", z=4)
txt(BX + 10.0, BY + BH - 8.7, "Wi-Fi + BLE 5", 6.0, TXT_DIM, ha="center", z=4)

ROW_A = ["3V3", "3V3", "RST", "4", "5", "6", "7", "15", "16", "17", "18",
         "8", "3", "46", "9", "10", "11", "12", "13", "14", "5V", "GND"]
ROW_B = ["GND", "GND", "19", "20", "21", "47", "48", "45", "0", "35", "36",
         "37", "38", "39", "40", "41", "42", "2", "1", "RX", "TX", "GND"]

PIN_TOP, PIN_STEP = 76.0, 3.05
PIN_W, PIN_H = 3.5, 1.9
AX_ = BX + BW - 4.6          # ряд A — правая кромка карточки
BX_ = BX + 1.1               # ряд B — левая кромка карточки

# сигналы, реально задействованные в проекте (индекс в ROW_A -> цвет, подпись)
USED = {
    0:  (W_3V3,   "3V3"),
    3:  (W_ADCA,  "ADC1_CH3"),
    4:  (W_ADCB,  "ADC1_CH4"),
    8:  (W_PWM,   "LEDC"),
    9:  (W_PROBE, "PROBE"),
    11: (W_SDA,   "SDA"),
    14: (W_SCL,   "SCL"),
    20: (W_5V,    "+5V"),
    21: (W_GND,   "GND"),
}
# запрещённые/занятые пины ряда B
BLOCKED_B = {2: "USB D-", 3: "USB D+", 7: "VDD_SPI", 8: "strap",
             9: "PSRAM", 10: "PSRAM", 11: "PSRAM", 19: "UART", 20: "UART"}

pin_y = {}
for i, name in enumerate(ROW_A):
    y = PIN_TOP - i * PIN_STEP
    pin_y[i] = y
    if i in USED:
        col, sig = USED[i]
        fc, ec, tc, lw = col, col, BG, 1.0
    else:
        fc, ec, tc, lw = "#1b2437", "#334155", TXT_FAINT, 0.8
    ax.add_patch(patches.FancyBboxPatch(
        (AX_, y - PIN_H / 2), PIN_W, PIN_H, boxstyle="round,pad=0.08,rounding_size=0.22",
        facecolor=fc, edgecolor=ec, linewidth=lw, zorder=4))
    ax.text(AX_ + PIN_W / 2, y, name, fontsize=6.6, fontweight="bold",
            color=tc, ha="center", va="center", zorder=5)
    if i in USED:
        ax.text(AX_ - 0.6, y, USED[i][1], fontsize=5.9, color=USED[i][0],
                ha="right", va="center", zorder=5, fontweight="bold")

for i, name in enumerate(ROW_B):
    y = PIN_TOP - i * PIN_STEP
    blocked = i in BLOCKED_B
    ax.add_patch(patches.FancyBboxPatch(
        (BX_, y - PIN_H / 2), PIN_W, PIN_H, boxstyle="round,pad=0.08,rounding_size=0.22",
        facecolor="#241a1f" if blocked else "#1b2437",
        edgecolor="#7f1d1d" if blocked else "#334155", linewidth=0.8, zorder=4))
    ax.text(BX_ + PIN_W / 2, y, name, fontsize=6.6, fontweight="bold",
            color="#b91c1c" if blocked else TXT_FAINT, ha="center", va="center", zorder=5)
    if blocked:
        ax.text(BX_ + PIN_W + 0.5, y, BLOCKED_B[i], fontsize=5.5, color="#b91c1c",
                ha="left", va="center", zorder=5)

txt(BX_ + PIN_W / 2, PIN_TOP + 2.6, "РЯД B", 7.0, TXT_DIM, ha="center", weight="bold")
txt(BX_ + PIN_W / 2, PIN_TOP + 1.5, "(GND · GND · 19…)", 5.6, TXT_FAINT, ha="center")
txt(AX_ + PIN_W / 2, PIN_TOP + 2.6, "РЯД A", 7.0, ACCENT, ha="center", weight="bold")
txt(AX_ + PIN_W / 2, PIN_TOP + 1.5, "(3V3 · 3V3 · RST…)", 5.6, TXT_FAINT, ha="center")

# памятка по запрещённым пинам
ax.add_patch(patches.FancyBboxPatch(
    (BX + 1.0, BY + 1.2), BW - 2.0, 5.3, boxstyle="round,pad=0.2,rounding_size=0.3",
    facecolor="#1a1114", edgecolor="#7f1d1d", linewidth=1.0, zorder=3))
txt(BX + BW / 2, BY + 5.4, "НЕ ИСПОЛЬЗОВАТЬ", 7.0, "#f87171", ha="center", weight="bold", z=5)
txt(BX + BW / 2, BY + 4.0, "35 · 36 · 37 — octal PSRAM (N16R8)", 6.0, "#fca5a5", ha="center", z=5)
txt(BX + BW / 2, BY + 2.9, "19 · 20 — USB    0 · 3 · 45 · 46 — strapping", 6.0, "#fca5a5", ha="center", z=5)
txt(BX + BW / 2, BY + 1.9, "11…20 — ADC2, не работает вместе с Wi-Fi", 6.0, "#fca5a5", ha="center", z=5)

# ============================================================================
# 2. ВХОД ПИТАНИЯ 12 В
# ============================================================================
PX, PY, PW, PH = 27.0, 68.0, 22.0, 22.0
card(PX, PY, PW, PH, "1 · ВХОД ПИТАНИЯ 12 В", "гнездо DC 5.5×2.5 → предохранитель → шина",
     border="#7f1d1d")

ax.add_patch(patches.FancyBboxPatch((PX + 1.5, PY + 10.5), 6.2, 4.6,
             boxstyle="round,pad=0.15,rounding_size=0.3", facecolor=CARD_DIM,
             edgecolor="#475569", linewidth=0.9, zorder=3))
txt(PX + 4.6, PY + 13.6, "БП 12 В / 3 А", 6.6, TXT, ha="center", weight="bold", z=5)
txt(PX + 4.6, PY + 12.4, "гнездо DC-099", 5.8, TXT_DIM, ha="center", z=5)
txt(PX + 4.6, PY + 11.3, "центр = «+»", 5.8, WARN, ha="center", z=5)

ax.add_patch(patches.FancyBboxPatch((PX + 9.2, PY + 11.6), 4.6, 2.5,
             boxstyle="round,pad=0.12,rounding_size=0.25", facecolor=CARD_DIM,
             edgecolor=WARN, linewidth=0.9, zorder=3))
txt(PX + 11.5, PY + 12.85, "ПРЕДОХР. 3 А", 5.8, WARN, ha="center", weight="bold", z=5)

# электролиты
for cx in (PX + 6.0, PX + 12.5):
    ax.add_patch(patches.Circle((cx, PY + 5.6), 2.05, facecolor="#1e293b",
                                edgecolor="#60a5fa", linewidth=1.1, zorder=3))
    ax.text(cx, PY + 6.1, "470 мкФ", fontsize=5.8, color=TXT, ha="center",
            va="center", zorder=5, fontweight="bold")
    ax.text(cx, PY + 5.0, "35 В", fontsize=5.5, color=TXT_DIM, ha="center",
            va="center", zorder=5)
txt(PX + PW / 2, PY + 2.4, "два электролита параллельно, вплотную ко входу", 6.0,
    TXT_DIM, ha="center")
txt(PX + PW / 2, PY + 1.3, "полоса на корпусе = «−» → на GND", 6.0, WARN, ha="center")

# шины внутри карточки
wire([(PX + 4.6, PY + 10.5), (PX + 4.6, PY + 9.0), (PX + 18.5, PY + 9.0)], W_12V, 2.0, dot_ends=False)
wire([(PX + 6.0, PY + 9.0), (PX + 6.0, PY + 7.65)], W_12V, 1.5, dot_ends=False)
wire([(PX + 12.5, PY + 9.0), (PX + 12.5, PY + 7.65)], W_12V, 1.5, dot_ends=False)
junction(PX + 6.0, PY + 9.0, W_12V)
junction(PX + 12.5, PY + 9.0, W_12V)
wire([(PX + 6.0, PY + 3.55), (PX + 6.0, PY + 3.0), (PX + 18.5, PY + 3.0)], W_GND, 2.0, dot_ends=False)
wire([(PX + 12.5, PY + 3.55), (PX + 12.5, PY + 3.0)], W_GND, 1.5, dot_ends=False)
junction(PX + 12.5, PY + 3.0, W_GND)
txt(PX + 15.0, PY + 9.7, "+12 В", 6.4, W_12V, weight="bold")
txt(PX + 15.0, PY + 3.7, "GND", 6.4, W_GND, weight="bold")

# ============================================================================
# 3. INA219
# ============================================================================
IX, IY, IW, IH = 51.0, 68.0, 22.0, 22.0
card(IX, IY, IW, IH, "2 · ТОКОВЫЙ МОНИТОР INA219",
     "шунт 0.1 Ом в разрыве «+12 В» (high-side)", border="#6d28d9")

ax.add_patch(patches.FancyBboxPatch((IX + 2.0, IY + 10.0), IW - 4.0, 6.0,
             boxstyle="round,pad=0.15,rounding_size=0.3", facecolor=CARD_DIM,
             edgecolor="#475569", linewidth=0.9, zorder=3))
txt(IX + 4.0, IY + 14.2, "Vin+", 6.6, W_12V, weight="bold", z=5)
txt(IX + IW - 4.0, IY + 14.2, "Vin−", 6.6, W_12V, ha="right", weight="bold", z=5)
txt(IX + IW / 2, IY + 12.7, "шунт R100 = 0.1 Ом", 6.4, TXT, ha="center", weight="bold", z=5)
txt(IX + IW / 2, IY + 11.4, "от БП →   → к катушке", 6.0, TXT_DIM, ha="center", z=5)

txt(IX + 2.6, IY + 7.6, "VCC → 3.3 В платы", 6.3, W_3V3, z=5)
txt(IX + 2.6, IY + 6.3, "GND → общая земля", 6.3, W_GND, z=5)
txt(IX + 2.6, IY + 5.0, "SDA → GPIO 8", 6.3, W_SDA, z=5)
txt(IX + 2.6, IY + 3.7, "SCL → GPIO 9", 6.3, W_SCL, z=5)
txt(IX + 2.6, IY + 2.2, "адрес I²C 0x40 · подтяжки на модуле", 5.8, TXT_FAINT, z=5)

# ============================================================================
# 4. СИЛОВАЯ ЧАСТЬ
# ============================================================================
SX, SY, SW, SH = 76.0, 34.0, 22.0, 56.0
card(SX, SY, SW, SH, "3 · СИЛОВАЯ ЧАСТЬ", "катушка · обратный диод · ключ", border="#b91c1c")

# катушка
ax.add_patch(patches.FancyBboxPatch((SX + 2.0, SY + 42.0), 9.0, 9.0,
             boxstyle="round,pad=0.15,rounding_size=0.3", facecolor="#2a1518",
             edgecolor=W_12V, linewidth=1.1, zorder=3))
txt(SX + 6.5, SY + 49.4, "ЭЛЕКТРОМАГНИТ", 6.6, TXT, ha="center", weight="bold", z=5)
txt(SX + 6.5, SY + 48.1, "JF-XP25×20", 6.2, TXT, ha="center", z=5)
txt(SX + 6.5, SY + 46.8, "12 В · ~25–30 Ом", 5.8, TXT_DIM, ha="center", z=5)
txt(SX + 6.5, SY + 45.5, "броневой (pot-core)", 5.8, TXT_DIM, ha="center", z=5)
txt(SX + 6.5, SY + 43.6, "L ≈ 20–60 мГн", 5.8, TXT_FAINT, ha="center", z=5)

# диод
ax.add_patch(patches.FancyBboxPatch((SX + 13.0, SY + 42.0), 7.0, 9.0,
             boxstyle="round,pad=0.15,rounding_size=0.3", facecolor="#1e293b",
             edgecolor=WARN, linewidth=1.1, zorder=3))
txt(SX + 16.5, SY + 49.4, "1N5822", 6.6, TXT, ha="center", weight="bold", z=5)
txt(SX + 16.5, SY + 48.1, "3 А / 40 В", 6.0, TXT_DIM, ha="center", z=5)
txt(SX + 16.5, SY + 46.4, "ПОЛОСА (катод)", 5.9, WARN, ha="center", weight="bold", z=5)
txt(SX + 16.5, SY + 45.2, "строго к +12 В", 5.9, WARN, ha="center", z=5)
txt(SX + 16.5, SY + 43.6, "параллельно катушке", 5.6, TXT_FAINT, ha="center", z=5)

# MOSFET
ax.add_patch(patches.FancyBboxPatch((SX + 2.0, SY + 20.0), 18.0, 15.0,
             boxstyle="round,pad=0.15,rounding_size=0.3", facecolor="#1e293b",
             edgecolor=W_DRAIN, linewidth=1.1, zorder=3))
txt(SX + 11.0, SY + 33.4, "IRLZ44N  (logic-level, TO-220)", 7.0, TXT, ha="center", weight="bold", z=5)
txt(SX + 11.0, SY + 32.0, "+ радиатор 20×15×10 мм", 6.0, TXT_DIM, ha="center", z=5)
txt(SX + 3.2, SY + 29.6, "1 · ЗАТВОР (G)", 6.4, W_PWM, weight="bold", z=5)
txt(SX + 3.2, SY + 28.3, "через 100 Ом → GPIO 16", 6.0, TXT_DIM, z=5)
txt(SX + 3.2, SY + 27.1, "10 кОм с затвора на GND", 6.0, TXT_DIM, z=5)
txt(SX + 3.2, SY + 25.2, "2 · СТОК (D)  → «−» катушки и анод диода", 6.4, W_DRAIN, weight="bold", z=5)
txt(SX + 3.2, SY + 23.3, "3 · ИСТОК (S) → звёздная земля", 6.4, W_GND, weight="bold", z=5)
txt(SX + 3.2, SY + 21.4, "фланец = сток! радиатор не заземлять", 5.8, "#fca5a5", z=5)

# резисторы затвора
ax.add_patch(patches.FancyBboxPatch((SX + 2.0, SY + 12.5), 18.0, 6.0,
             boxstyle="round,pad=0.15,rounding_size=0.3", facecolor=CARD_DIM,
             edgecolor="#334155", linewidth=0.9, zorder=3))
txt(SX + 11.0, SY + 17.0, "ЦЕПЬ ЗАТВОРА", 6.4, TXT, ha="center", weight="bold", z=5)
txt(SX + 11.0, SY + 15.4, "GPIO 16 ──[100 Ом]──┬── G", 6.4, TXT_DIM, ha="center", z=5)
txt(SX + 11.0, SY + 14.1, "                    └──[10 кОм]── GND", 6.4, TXT_DIM, ha="center", z=5)

txt(SX + 11.0, SY + 10.4, "ШИМ 20 кГц · 11 бит (0…2047)", 6.6, W_PWM, ha="center", weight="bold", z=5)
txt(SX + 11.0, SY + 9.0, "ниже 18 кГц катушка свистит", 5.8, TXT_FAINT, ha="center", z=5)
txt(SX + 11.0, SY + 6.6, "ВСЯ ЭТА ЧАСТЬ — ТОЛЬКО ПАЙКА", 6.6, "#f87171", ha="center", weight="bold", z=5)
txt(SX + 11.0, SY + 5.2, "на беспаечной макетке импульсный ток 1–2 А", 5.8, TXT_FAINT, ha="center", z=5)
txt(SX + 11.0, SY + 4.0, "даёт наводки, похожие на шум датчика", 5.8, TXT_FAINT, ha="center", z=5)

# внутренние соединения силовой части
wire([(SX + 6.5, SY + 42.0), (SX + 6.5, SY + 38.0), (SX + 11.0, SY + 38.0),
      (SX + 11.0, SY + 35.0)], W_DRAIN, 2.0, dot_ends=False)
wire([(SX + 16.5, SY + 42.0), (SX + 16.5, SY + 38.0), (SX + 11.0, SY + 38.0)], W_DRAIN, 2.0, dot_ends=False)
junction(SX + 11.0, SY + 38.0, W_DRAIN)
tag(SX + 11.0, SY + 40.0, "СТОК", W_DRAIN, 6.2)
wire([(SX + 6.5, SY + 51.0), (SX + 6.5, SY + 53.5), (SX + 16.5, SY + 53.5),
      (SX + 16.5, SY + 51.0)], W_12V, 2.0, dot_ends=False)
junction(SX + 6.5, SY + 53.5, W_12V)
tag(SX + 11.0, SY + 53.5, "+12 В", W_12V, 6.2)

# ============================================================================
# 5. ДАТЧИКИ ХОЛЛА
# ============================================================================
HX, HY, HW, HH = 27.0, 34.0, 46.0, 30.0
card(HX, HY, HW, HH, "4 · ДИФФЕРЕНЦИАЛЬНАЯ ПАРА ДАТЧИКОВ ХОЛЛА SS49E",
     "делители 1:2 обязательны — выход датчика доходит до 5 В, вход АЦП терпит 3.3 В",
     border="#0e7490")

for k, (label, col, pin, x0) in enumerate([
        ("ДАТЧИК A", W_ADCA, "GPIO 4", HX + 2.0),
        ("ДАТЧИК B", W_ADCB, "GPIO 5", HX + 24.0)]):
    ax.add_patch(patches.FancyBboxPatch((x0, HY + 3.0), 20.0, 21.0,
                 boxstyle="round,pad=0.15,rounding_size=0.3", facecolor=CARD_DIM,
                 edgecolor=col, linewidth=1.0, zorder=3))
    txt(x0 + 10.0, HY + 22.6, f"{label}  (SS49E, TO-92)", 7.0, TXT, ha="center", weight="bold", z=5)
    txt(x0 + 1.5, HY + 20.4, "плоской стороной к себе, ножками вниз:", 5.9, TXT_FAINT, z=5)
    txt(x0 + 1.5, HY + 19.1, "1 = VCC (+5 В)   2 = GND   3 = OUT", 6.2, TXT, z=5)
    txt(x0 + 1.5, HY + 17.6, "0.1 мкФ между 1 и 2, вплотную к корпусу", 5.9, W_3V3, z=5)
    txt(x0 + 1.5, HY + 15.6, "покой ≈ 2.5 В, размах 1.0…4.0 В", 6.0, TXT_DIM, z=5)

    # делитель
    ax.add_patch(patches.FancyBboxPatch((x0 + 1.2, HY + 4.2), 17.6, 10.0,
                 boxstyle="round,pad=0.12,rounding_size=0.25", facecolor="#0b1220",
                 edgecolor="#334155", linewidth=0.8, zorder=4))
    txt(x0 + 10.0, HY + 12.9, "ДЕЛИТЕЛЬ 1:2", 6.4, col, ha="center", weight="bold", z=6)
    txt(x0 + 10.0, HY + 11.2, "OUT ──[10 кОм]──┬──[10 кОм]── GND", 6.4, TXT, ha="center", z=6)
    txt(x0 + 10.0, HY + 9.7, "│", 6.4, TXT, ha="center", z=6)
    txt(x0 + 10.0, HY + 8.3, f"средняя точка → {pin}", 6.4, col, ha="center", weight="bold", z=6)
    txt(x0 + 10.0, HY + 6.7, "на входе АЦП 0.5…2.0 В, в покое ≈ 1.25 В", 5.9, TXT_DIM, ha="center", z=6)
    txt(x0 + 10.0, HY + 5.3, "проверить мультиметром ДО подключения к плате", 5.9, WARN, ha="center", z=6)

txt(HX + HW / 2, HY + 1.6,
    "положение = OUT_A − OUT_B  •  синфазная наводка от тока катушки вычитается, "
    "остаток компенсируется программно",
    6.2, ACCENT, ha="center")

# ============================================================================
# 6. ГЕОМЕТРИЯ
# ============================================================================
GX, GY, GW, GH = 27.0, 7.5, 46.0, 22.0
card(GX, GY, GW, GH, "5 · ГЕОМЕТРИЯ УЗЛА", border="#334155")
txt(GX + 1.5, GY + 19.6, "вид сбоку, масштаб условный", 5.8, TXT_FAINT, z=5)

ax.add_patch(patches.Rectangle((GX + 16.0, GY + 14.5), 12.0, 5.0,
             facecolor="#334155", edgecolor="#94a3b8", linewidth=1.0, zorder=3))
txt(GX + 22.0, GY + 16.9, "ЭЛЕКТРОМАГНИТ", 6.2, TXT, ha="center", weight="bold", z=5)
ax.add_patch(patches.Rectangle((GX + 20.8, GY + 13.6), 2.4, 0.9,
             facecolor="#64748b", edgecolor="#cbd5e1", linewidth=0.8, zorder=4))

for sx, lbl, col in [(GX + 12.0, "SS49E A", W_ADCA), (GX + 32.0, "SS49E B", W_ADCB)]:
    ax.add_patch(patches.Rectangle((sx - 0.9, GY + 14.0), 1.8, 2.6,
                 facecolor="#1e293b", edgecolor=col, linewidth=1.0, zorder=4))
    txt(sx, GY + 17.4, lbl, 5.8, col, ha="center", weight="bold", z=5)
    txt(sx, GY + 13.0, "5–8 мм от оси", 5.4, TXT_FAINT, ha="center", z=5)

ax.add_patch(patches.Circle((GX + 22.0, GY + 10.5), 1.5, facecolor="#475569",
                            edgecolor="#e2e8f0", linewidth=1.0, zorder=4))
txt(GX + 22.0, GY + 10.5, "ШХ15\n10 мм", 5.4, TXT, ha="center", z=5)

ax.annotate("", xy=(GX + 25.5, GY + 13.6), xytext=(GX + 25.5, GY + 12.0),
            arrowprops=dict(arrowstyle="<->", color=WARN, linewidth=1.2), zorder=5)
txt(GX + 26.4, GY + 12.8, "x₀\n2.5 мм", 6.2, WARN, weight="bold", z=6)
txt(GX + 22.0, GY + 8.1, "полюсный наконечник M4 — вариант Б, если поля не хватит",
    5.5, TXT_FAINT, ha="center", z=5)

txt(GX + 1.5, GY + 6.0,
    "Зазор 2.5 мм, а не «классические» 10–15 мм: JF-XP25×20 — броневой удерживающий магнит,",
    6.0, TXT_DIM, z=5)
txt(GX + 1.5, GY + 4.8,
    "поток замыкается между керном и стаканом на торце и почти не выходит в воздух дальше 2–3 мм.",
    6.0, TXT_DIM, z=5)
txt(GX + 1.5, GY + 3.6,
    "Следствие: объект «жёстче», неустойчивый полюс быстрее → петля управления строго ≥ 1 кГц.",
    6.0, ACCENT, z=5)
txt(GX + 1.5, GY + 2.2,
    "Стойка должна держать зазор без дрожания: люфт 0.5 мм — это 20 % рабочего диапазона.",
    6.0, WARN, z=5)

# ============================================================================
# 7. ЗВЁЗДНАЯ ЗЕМЛЯ
# ============================================================================
EX, EY, EW, EH = 76.0, 7.5, 22.0, 22.0
card(EX, EY, EW, EH, "6 · ЗВЁЗДНАЯ ЗЕМЛЯ", "все «минусы» сходятся в одной точке", border="#475569")
txt(EX + EW / 2, EY + 17.6, "ТОЧКА СВЕДЕНИЯ — У ИСТОКА MOSFET", 6.4, TXT, ha="center", weight="bold", z=5)
for i, s in enumerate([
        "1 · исток IRLZ44N",
        "2 · «−» блока питания 12 В",
        "3 · «−» электролитов 470 мкФ",
        "4 · GND платы ESP32-S3",
        "5 · нижние выводы делителей",
        "6 · GND датчиков Холла",
        "7 · GND модуля INA219"]):
    txt(EX + 2.5, EY + 15.6 - i * 1.55, s, 6.2, TXT_DIM, z=5)
txt(EX + EW / 2, EY + 3.4, "земля силовая и земля сигнальная —", 6.0, WARN, ha="center", z=5)
txt(EX + EW / 2, EY + 2.2, "разными проводами до общей точки", 6.0, WARN, ha="center", z=5)

# ============================================================================
# 8. ПРОВОДА
# ============================================================================
CH = AX_ + PIN_W          # правая кромка ряда A
L1, L2, L3, L4 = 91.2, 92.0, 92.8, 90.4     # верхние коридоры
LOW_5V, LOW_GND = 32.2, 31.0                # нижние коридоры
TOP = IY + IH                               # верхняя кромка карточек второго ряда

# 3V3 -> INA219 (VCC логики)
wire([(CH, pin_y[0]), (CH + 1.0, pin_y[0]), (CH + 1.0, L4), (IX + 3.5, L4),
      (IX + 3.5, TOP)], W_3V3)
tag(41.0, L4, "3.3 В → VCC INA219", W_3V3)

# ШИМ -> затвор
wire([(CH, pin_y[8]), (CH + 2.4, pin_y[8]), (CH + 2.4, L1), (SX + 11.0, L1),
      (SX + 11.0, SY + SH)], W_PWM)
tag(52.0, L1, "ШИМ 20 кГц · GPIO 16 → 100 Ом → затвор", W_PWM)

# SDA
wire([(CH, pin_y[11]), (CH + 3.1, pin_y[11]), (CH + 3.1, L2), (IX + 9.0, L2),
      (IX + 9.0, TOP)], W_SDA)
tag(36.0, L2, "SDA · GPIO 8", W_SDA)

# SCL
wire([(CH, pin_y[14]), (CH + 3.8, pin_y[14]), (CH + 3.8, L3), (IX + 14.5, L3),
      (IX + 14.5, TOP)], W_SCL)
tag(36.0, L3, "SCL · GPIO 9", W_SCL)

# ADC A / ADC B — до левой кромки карточки датчиков
wire([(CH, pin_y[3]), (CH + 1.7, pin_y[3]), (CH + 1.7, HY + 15.0), (HX, HY + 15.0)], W_ADCA)
tag(CH + 1.9, HY + 21.5, "GPIO 4", W_ADCA)
wire([(CH, pin_y[4]), (CH + 1.0, pin_y[4]), (CH + 1.0, HY + 11.0), (HX, HY + 11.0)], W_ADCB)
tag(CH + 1.1, HY + 18.5, "GPIO 5", W_ADCB)

# метка времени на осциллограф — отдельный тонкий провод, свой коридор
wire([(CH, pin_y[9]), (CH + 0.5, pin_y[9]), (CH + 0.5, 65.6), (HX + 3.0, 65.6)], W_PROBE, 1.2)
tag(HX + 12.5, 65.6, "GPIO 17 → метка времени шага регулятора", W_PROBE, 6.2)

# +5 В на датчики
wire([(CH, pin_y[20]), (CH + 1.4, pin_y[20]), (CH + 1.4, LOW_5V), (HX + 8.0, LOW_5V),
      (HX + 8.0, HY)], W_5V)
wire([(HX + 8.0, LOW_5V), (HX + 30.0, LOW_5V), (HX + 30.0, HY)], W_5V, dot_ends=False)
junction(HX + 8.0, LOW_5V, W_5V)
tag(HX + 19.0, LOW_5V, "+5 В (пин 5V платы) → VCC обоих SS49E", W_5V, 6.2)

# земля платы -> звезда
wire([(CH, pin_y[21]), (CH + 2.0, pin_y[21]), (CH + 2.0, LOW_GND), (EX + 11.0, LOW_GND),
      (EX + 11.0, EY + EH)], W_GND, 2.0)
tag(GX + 34.0, LOW_GND, "GND платы → звёздная земля", W_GND, 6.2)

# +12 В: вход -> INA219 -> катушка
wire([(PX + PW, PY + 14.2), (IX, IY + 14.2)], W_12V, 2.2)
tag((PX + PW + IX) / 2, PY + 16.0, "+12 В", W_12V)
wire([(IX + IW, IY + 14.2), (74.6, IY + 14.2), (74.6, SY + 53.5), (SX + 6.5, SY + 53.5)], W_12V, 2.2)
tag(74.6, 79.0, "+12 В\nна катушку", W_12V, 6.0)

# земля силовой шины -> исток -> звезда
wire([(PX + PW - 3.5, PY + 3.0), (49.9, PY + 3.0), (49.9, 67.2), (73.4, 67.2),
      (73.4, SY + 23.3), (SX, SY + 23.3)], W_GND, 2.2)
tag(61.5, 67.2, "GND силовой шины → исток MOSFET → звезда", W_GND, 6.2)

# ============================================================================
# 9. ЛЕГЕНДА
# ============================================================================
card(2, 0.8, 96, 5.4, "", "", bg=CARD_DIM, border=BORDER)

legend = [
    (W_12V,   "+12 В силовая"),
    (W_DRAIN, "сток / «−» катушки"),
    (W_5V,    "+5 В датчики"),
    (W_3V3,   "+3.3 В логика"),
    (W_GND,   "GND (звезда)"),
    (W_PWM,   "ШИМ GPIO 16"),
    (W_ADCA,  "ADC GPIO 4"),
    (W_ADCB,  "ADC GPIO 5"),
    (W_SDA,   "SDA GPIO 8"),
    (W_SCL,   "SCL GPIO 9"),
    (W_PROBE, "PROBE GPIO 17"),
]
x = 3.8
for col, lbl in legend:
    ax.plot([x, x + 1.8], [4.6, 4.6], color=col, linewidth=2.4, zorder=6)
    txt(x + 2.2, 4.6, lbl, 6.2, TXT_DIM)
    x += 8.4

rules = [
    ("1", "Полоса 1N5822 (катод) — строго на +12 В."),
    ("2", "Без делителя 10к/10к вход АЦП сгорает."),
    ("3", "Аналог только на ADC1 (GPIO 1…10): ADC2 глушится Wi-Fi."),
    ("4", "GPIO 35/36/37 заняты octal PSRAM N16R8."),
]
x = 3.8
for n, s in rules:
    txt(x, 2.3, f"{n}.", 6.4, WARN, weight="bold")
    txt(x + 1.1, 2.3, s, 6.1, TXT_DIM)
    x += 23.5

# ----------------------------------------------------------------------------
if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    fig.savefig(os.path.join(here, "schematic.png"), dpi=300,
                facecolor=BG, bbox_inches="tight", pad_inches=0.15)
    fig.savefig(os.path.join(here, "schematic.svg"),
                facecolor=BG, bbox_inches="tight", pad_inches=0.15)
    print("saved: schematic.png, schematic.svg")

    from build_page import build_html      # собираем автономную HTML-страницу
    build_html(here)
