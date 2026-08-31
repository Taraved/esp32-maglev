#!/usr/bin/env python3
"""
Карта соединений маглев-стенда: какой узел с каким связан и сколько
между ними проводов.

Главное, что показывает карта: ESP32-S3, INA219 и делители стоят на ОДНОЙ
макетке, поэтому большая часть из девяти задействованных контактов платы
соединяется короткими перемычками внутри макетки, а наружу уходит всего
семь проводов.

Выход: interconnect.png (300 dpi), interconnect.svg

Запуск (окружение проекта):
    /Users/master/Projects/venv/bin/python3 interconnect.py
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches

BG, CARD, BORDER = "#0b0f19", "#131b2e", "#233554"
TXT, TXT_DIM, TXT_FAINT = "#f8fafc", "#94a3b8", "#64748b"
C_SIG, C_GND, C_5V, C_I2C = "#eab308", "#94a3b8", "#f97316", "#a855f7"
C_12V, C_COIL, C_ADC = "#ef4444", "#f43f5e", "#06b6d4"
ACCENT, WARN, DIM_BLOCK = "#38bdf8", "#fbbf24", "#1a2333"

fig, ax = plt.subplots(figsize=(18, 11), dpi=300, facecolor=BG)
ax.set_facecolor(BG)
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")
fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)


def block(x, y, w, h, title, lines, edge=BORDER, face=CARD, tcol=TXT,
          dashed=False, ts=11.5, ls=8.2, z=3):
    ax.add_patch(patches.FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.35,rounding_size=0.7",
        facecolor=face, edgecolor=edge, linewidth=1.7, zorder=z,
        linestyle=(0, (5, 3)) if dashed else "solid"))
    ax.text(x + w / 2, y + h - 2.2, title, ha="center", va="center",
            fontsize=ts, fontweight="bold", color=tcol, zorder=z + 2)
    for i, s in enumerate(lines):
        ax.text(x + w / 2, y + h - 4.9 - i * 2.3, s, ha="center", va="center",
                fontsize=ls, color=TXT_DIM, zorder=z + 2)


def link(pts, color, label, n, at, lw=2.2, dashed=False):
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color=color, linewidth=lw,
            zorder=6, solid_capstyle="round",
            linestyle=(0, (6, 4)) if dashed else "solid")
    ax.plot([pts[0][0], pts[-1][0]], [pts[0][1], pts[-1][1]], "o",
            color=color, markersize=4.5, zorder=7)
    lx, ly = at
    ax.text(lx, ly, label, ha="center", va="center", fontsize=8.5,
            fontweight="bold", color=color, zorder=10,
            bbox=dict(boxstyle="round,pad=0.3", facecolor=BG, edgecolor=color, linewidth=1.0))
    ax.text(lx, ly - 2.4, n, ha="center", va="center", fontsize=7.6,
            color=TXT_FAINT, zorder=10,
            bbox=dict(boxstyle="round,pad=0.15", facecolor=BG, edgecolor="none"))


def jumper(pts, color, label, at):
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color=color, linewidth=1.5,
            zorder=6, linestyle=(0, (3, 2)), solid_capstyle="round")
    ax.text(at[0], at[1], label, ha="center", va="center", fontsize=7.4,
            color=color, fontweight="bold", zorder=10,
            bbox=dict(boxstyle="round,pad=0.22", facecolor=BG, edgecolor=color, linewidth=0.7))


# =============================== BREADBOARD ==================================
ax.add_patch(patches.FancyBboxPatch(
    (2, 36), 50, 55, boxstyle="round,pad=0.5,rounding_size=1.0",
    facecolor="#0e1424", edgecolor=ACCENT, linewidth=2.4, zorder=2))
ax.text(27, 88.6, "БЕСПАЕЧНАЯ МАКЕТКА (BREADBOARD)", ha="center", va="center",
        fontsize=13.5, fontweight="bold", color=ACCENT, zorder=5)
ax.text(27, 85.7, "всё, что здесь внутри, соединяется короткими перемычками —",
        ha="center", va="center", fontsize=8.6, color=TXT_DIM, zorder=5)
ax.text(27, 83.4, "это не «провода наружу»",
        ha="center", va="center", fontsize=8.6, color=TXT_DIM, zorder=5)

block(5, 58, 21, 23, "ESP32-S3", ["воткнута в макетку", "", "9 задействованных",
                                  "контактов — все", "на ряду A"],
      edge=ACCENT, face=DIM_BLOCK, ts=11, ls=8.0, z=4)
block(29, 58, 20, 23, "INA219", ["воткнут в макетку", "", "нужны 4 контакта:",
                                 "VCC · GND · SDA · SCL"],
      edge=C_I2C, face=DIM_BLOCK, ts=11, ls=8.0, z=4)
block(5, 39, 44, 15, "4 × 10 кОм — ДЕЛИТЕЛИ 1:2",
      ["стоят здесь, рядом с АЦП, а не у датчика:",
       "так по длинному проводу идёт сигнал",
       "с низким выходным сопротивлением SS49E"],
      edge=C_ADC, face=DIM_BLOCK, ts=10.5, ls=8.0, z=4)

jumper([(26, 76), (29, 76)], C_I2C, "GPIO 8 · 9 · 3V3 · GND", (27.5, 79.6))
jumper([(11, 58), (11, 54)], C_ADC, "GPIO 4 · GPIO 5", (13.5, 56.2))
jumper([(43, 58), (43, 54)], C_GND, "GND", (44.5, 56.2))

# ============================== ОСТАЛЬНЫЕ УЗЛЫ ================================
block(2, 6, 30, 24, "КРОНШТЕЙН У МАГНИТА",
      ["2 × SS49E + керамика 0.1 мкФ", "", "ставится на магнит,",
       "положение подбирается", "экспериментально"], edge=C_5V)

block(59, 30, 29, 42, "СИЛОВАЯ ПЛАТА",
      ["IRLZ44N · 1N5822", "2 × 470 мкФ · J1 · J2", "",
       "паяется 3 провода:", "1 сигнальный + 2 земли", "",
       "звёздная земля — здесь,", "у истока транзистора"], edge=C_12V)

block(89, 52, 10, 18, "МАГНИТ", ["JF-XP25×20", "", "2 провода", "в J2"],
      edge=C_COIL, ts=10, ls=7.6)
block(89, 24, 10, 18, "БП 12 В", ["12 В / 3 А", "", "2 провода", "в J1"],
      edge=C_12V, ts=10, ls=7.6)

# ================================= СВЯЗИ =====================================
link([(52, 70), (59, 70)], C_SIG, "GPIO 16 → 100 Ом", "1 провод", at=(55.5, 76.5))
link([(52, 64), (55.5, 64), (55.5, 62), (59, 62)], C_GND,
     "GND цифровая", "1 провод", at=(55.5, 68.0))
link([(52, 44), (55.5, 44), (55.5, 50), (59, 50)], C_GND,
     "GND аналоговая", "1 провод", at=(55.5, 55.5))
link([(49, 62), (53.5, 62), (53.5, 34), (59, 34)], C_12V,
     "разрыв +12 В", "2 провода", at=(50.0, 32.0), dashed=True)

link([(16, 36), (16, 30)], C_5V, "+5 В · GND · OUT_A · OUT_B", "4 провода", at=(16, 33.6))
link([(89, 60), (88, 60)], C_COIL, "катушка", "2 провода, винты", at=(83.5, 63.5))
link([(89, 33), (88, 33)], C_12V, "12 В", "2 провода, винты", at=(83.5, 36.5))

# ============================ СЧЁТЧИК ПРОВОДОВ ================================
ax.add_patch(patches.FancyBboxPatch(
    (59, 6), 40, 19, boxstyle="round,pad=0.4,rounding_size=0.8",
    facecolor="#0f1626", edgecolor=WARN, linewidth=1.6, zorder=3))
ax.text(79, 22.6, "НАРУЖУ С МАКЕТКИ — 7 ПРОВОДОВ", ha="center", va="center",
        fontsize=11, fontweight="bold", color=WARN, zorder=5)
counts = [
    ("3", "на силовую плату: GPIO 16 и две земли", C_SIG),
    ("4", "на кронштейн: +5 В, GND, OUT_A, OUT_B", C_5V),
    ("+2", "от INA219 в разрыв +12 В — когда включите его в цепь", C_12V),
]
for i, (n, t, c) in enumerate(counts):
    y = 18.6 - i * 3.2
    ax.text(62, y, n, ha="left", va="center", fontsize=11, fontweight="bold",
            color=c, zorder=5)
    ax.text(65.5, y, t, ha="left", va="center", fontsize=8.5, color=TXT_DIM, zorder=5)
ax.text(79, 8.4, "Остальные соединения — перемычки внутри макетки.",
        ha="center", va="center", fontsize=8.5, color=TXT_FAINT, zorder=5)

# ================================ ЗАГОЛОВОК ==================================
ax.text(50, 97.5, "КАРТА СОЕДИНЕНИЙ: КТО С КЕМ И СКОЛЬКИМИ ПРОВОДАМИ",
        ha="center", va="center", fontsize=17, fontweight="bold", color=TXT)
ax.text(50, 94.2,
        "«девять» — это задействованные контакты платы ESP32-S3, а не провода в одно место: "
        "ESP32, INA219 и делители стоят на одной макетке",
        ha="center", va="center", fontsize=10.5, color=TXT_DIM)

if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    fig.savefig(os.path.join(here, "interconnect.png"), dpi=300,
                facecolor=BG, bbox_inches="tight", pad_inches=0.2)
    fig.savefig(os.path.join(here, "interconnect.svg"),
                facecolor=BG, bbox_inches="tight", pad_inches=0.2)
    print("saved: interconnect.png, interconnect.svg")
