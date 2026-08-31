#!/usr/bin/env python3
"""
Раскладка силовой платы маглев-стенда на перфоплате 14 x 20
(столбцы 01-14, строки A-T, шаг 2.54 мм, плата двусторонняя с металлизацией).

Рисует две панели:
  ВИД СВЕРХУ  — где стоят компоненты и как они ориентированы
  ВИД СНИЗУ   — дорожки припоем; панель ЗЕРКАЛЬНА, как плата лежит при пайке

Выход: board_layout.png (300 dpi), board_layout.svg

Запуск (окружение проекта):
    /Users/master/Projects/venv/bin/python3 board_layout.py
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches

BG, TXT, TXT_DIM, TXT_FAINT = "#0b0f19", "#f8fafc", "#94a3b8", "#64748b"
PAD_RING, PAD_HOLE = "#475569", "#0b0f19"
PCB_FACE, PCB_EDGE = "#0d2818", "#15803d"

C_12V, C_GND, C_DRAIN, C_GATE = "#ef4444", "#94a3b8", "#f43f5e", "#eab308"
C_PIN, ACCENT, WARN = "#ffffff", "#38bdf8", "#fbbf24"

ROWS = "ABCDEFGHIJKLMNOPQRST"
COLS = list(range(1, 15))


def parse(ref):
    """'H03' -> (столбец, строка) в координатах сетки."""
    return int(ref[1:]), ROWS.index(ref[0]) + 1


def ry(row):
    return ROWS.index(row) + 1


# --- дорожки нижней стороны: столбец, строка_от, строка_до, цвет, подпись, толщина
TRACKS = [
    (3, "A", "O", C_12V,   "+12 В",          6.5),
    (5, "B", "T", C_GND,   "GND",            6.5),
    (7, "G", "T", C_DRAIN, "СТОК",           6.5),
    (9, "G", "L", C_12V,   "+12 В отвод",    5.5),
    (9, "R", "T", C_GATE,  "ЗАТВОР",         2.8),
]

JUMPERS = [("L03", "L09", C_12V)]

# метка, подпись, отверстия, (col0, col1, row0, row1), цвет заливки
PARTS = [
    ("J1", "клеммник ввода 12 В",  ["B03", "B05"], (2.05, 5.95, "A", "E"), "#7f1d1d"),
    ("J2", "клеммник катушки",     ["G07", "G09"], (6.05, 9.95, "E", "I"), "#7f1d1d"),
    ("C1", "470 мкФ 35 В",         ["H03", "H05"], (2.05, 5.95, "F", "J"), "#1d4ed8"),
    ("D1", "1N5822",               ["K07", "K09"], (6.40, 9.60, "J", "L"), "#a16207"),
    ("C2", "470 мкФ 35 В",         ["O03", "O05"], (2.05, 5.95, "M", "Q"), "#1d4ed8"),
    ("R2", "10 кОм",               ["R05", "R09"], (4.55, 9.45, "R", "R"), "#334155"),
    ("R1", "100 Ом",               ["S09", "S13"], (8.55, 13.45, "S", "S"), "#334155"),
    ("Q1", "IRLZ44N + радиатор",   ["T05", "T07", "T09"], (4.10, 9.90, "T", "T"), "#be123c"),
]

# подписи выводов прямо у отверстий (вид сверху)
# ref, подпись, dx, dy, выравнивание
PIN_NOTES = [
    ("B03", "+12 В",  -0.55, 0.0,  "right"), ("B05", "GND",   0.55, 0.0, "left"),
    ("H03", "+",      -0.55, 0.0,  "right"), ("H05", "−",     0.55, 0.0, "left"),
    ("O03", "+",      -0.55, 0.0,  "right"), ("O05", "−",     0.55, 0.0, "left"),
    ("G09", "+12 В",   0.0, -0.85, "center"), ("G07", "«−» катушки", 0.0, -0.85, "center"),
    ("K09", "катод (полоса)", 0.55, 0.0, "left"), ("K07", "анод", -0.55, 0.0, "right"),
    ("T05", "S", 0.42, 0.0, "left"), ("T07", "D", 0.42, 0.0, "left"),
    ("T09", "G", 0.42, 0.0, "left"),
]

WIRES = [
    ("S13", "провод → GPIO 16", C_GATE),
    ("P05", "провод → GND платы ESP32-S3", C_GND),
]

fig, axes = plt.subplots(1, 2, figsize=(22, 12.5), dpi=300, facecolor=BG)
fig.subplots_adjust(left=0.02, right=0.98, top=0.885, bottom=0.03, wspace=0.16)


def draw_grid(ax, mirror, title, subtitle, sub_col):
    ax.set_facecolor(BG)
    ax.set_xlim(-1.2, 18.6)
    ax.set_ylim(22.4, -2.2)
    ax.set_aspect("equal")
    ax.axis("off")

    def X(c):
        return 15 - c if mirror else c

    ax.add_patch(patches.FancyBboxPatch(
        (0.1, 0.1), 14.8, 20.8, boxstyle="round,pad=0.35,rounding_size=0.4",
        facecolor=PCB_FACE, edgecolor=PCB_EDGE, linewidth=2.2, zorder=1))
    ax.text(7.5, -1.6, title, ha="center", va="center", fontsize=15.5,
            fontweight="bold", color=TXT, zorder=9)
    ax.text(7.5, -0.85, subtitle, ha="center", va="center", fontsize=9.5,
            color=sub_col, zorder=9)

    for r in range(1, 21):
        for c in COLS:
            ax.add_patch(patches.Circle((X(c), r), 0.30, facecolor=PAD_HOLE,
                                        edgecolor=PAD_RING, linewidth=1.1, zorder=3))
    for r_i, r_name in enumerate(ROWS, start=1):
        for xx in (X(0.25), X(14.75)):
            ax.text(xx, r_i, r_name, ha="center", va="center", fontsize=8,
                    color=TXT_FAINT, zorder=4)
    for c in COLS:
        for yy in (0.2, 20.8):
            ax.text(X(c), yy, f"{c:02d}", ha="center", va="center", fontsize=7.5,
                    color=TXT_FAINT, zorder=4)
    return X


# ---------------------------- ПАНЕЛЬ 1: СВЕРХУ ------------------------------
ax = axes[0]
draw_grid(ax, False, "ВИД СВЕРХУ — где что стоит",
          "компоненты ставятся с этой стороны, выводы уходят вниз", TXT_DIM)

for label, desc, holes, (c0, c1, r0, r1), colr in PARTS:
    y0, y1 = ry(r0) - 0.45, ry(r1) + 0.45
    ax.add_patch(patches.FancyBboxPatch(
        (c0, y0), c1 - c0, y1 - y0, boxstyle="round,pad=0.08,rounding_size=0.22",
        facecolor=colr, edgecolor="#e2e8f0", linewidth=1.2, alpha=0.32, zorder=5))
    cx, cy = (c0 + c1) / 2, (y0 + y1) / 2
    dy = 0.30 if (y1 - y0) > 1.4 else 0.0
    ax.text(cx, cy - dy, label, ha="center", va="center", fontsize=12,
            fontweight="bold", color=TXT, zorder=7)
    if dy:
        ax.text(cx, cy + 0.62, desc, ha="center", va="center", fontsize=7.6,
                color="#e2e8f0", zorder=7)
    else:
        ax.text(c1 + 0.35, cy, f"{desc}", ha="left", va="center", fontsize=7.6,
                color="#e2e8f0", zorder=7)
    for h in holes:
        hx, hy = parse(h)
        ax.add_patch(patches.Circle((hx, hy), 0.34, facecolor=C_PIN,
                                    edgecolor=BG, linewidth=1.0, zorder=8))

for ref, note, dx, dy, ha in PIN_NOTES:
    hx, hy = parse(ref)
    ax.text(hx + dx, hy + dy, note, ha=ha, va="center", fontsize=6.8,
            color=WARN, fontweight="bold", zorder=10,
            bbox=dict(boxstyle="round,pad=0.15", facecolor=BG, edgecolor="none", alpha=0.85))

for jf, jt, jc in JUMPERS:
    x0, y0 = parse(jf)
    x1, y1 = parse(jt)
    ax.plot([x0, x1], [y0, y1], color=jc, linewidth=4.2, zorder=6, solid_capstyle="round")
    ax.plot([x0, x1], [y0, y1], color="#ffffff", linewidth=1.1, zorder=7, linestyle=(0, (2, 2)))
    ax.text(x1 + 1.7, y1, "ПЕРЕМЫЧКА СВЕРХУ\nлужёный провод", ha="left", va="center",
            fontsize=7.2, fontweight="bold", color=jc, zorder=11,
            bbox=dict(boxstyle="round,pad=0.2", facecolor=BG, edgecolor=jc, linewidth=0.8))

for ref, desc, colr in WIRES:
    hx, hy = parse(ref)
    ax.add_patch(patches.Circle((hx, hy), 0.34, facecolor=colr, edgecolor=BG,
                                linewidth=1.0, zorder=8))
    ax.annotate("", xy=(15.6, hy), xytext=(14.9, hy),
                arrowprops=dict(arrowstyle="->", color=colr, linewidth=1.8), zorder=9)
    ax.plot([hx, 14.9], [hy, hy], color=colr, linewidth=1.4, zorder=6,
            linestyle=(0, (4, 3)))
    ax.text(15.8, hy, desc, ha="left", va="center", fontsize=7.8,
            color=colr, fontweight="bold", zorder=9)

# ---------------------------- ПАНЕЛЬ 2: СНИЗУ -------------------------------
ax = axes[1]
X = draw_grid(ax, True, "ВИД СНИЗУ — дорожки припоем",
              "панель ЗЕРКАЛЬНА: столбец 01 справа — так плата лежит при пайке", WARN)

label_y = {3: -0.05, 5: -0.05, 7: 5.15, 9: 5.15}
for col_i, r_from, r_to, colr, name, lw in TRACKS:
    y0, y1 = ry(r_from), ry(r_to)
    xx = X(col_i)
    ax.plot([xx, xx], [y0, y1], color=colr, linewidth=lw, zorder=6,
            solid_capstyle="round", alpha=0.95)
    if name != "ЗАТВОР":
        ax.text(xx, y0 - 0.9, name, ha="center", va="center", fontsize=7.2,
                fontweight="bold", color=colr, zorder=10,
                bbox=dict(boxstyle="round,pad=0.22", facecolor=BG,
                          edgecolor=colr, linewidth=0.8))
    else:
        ax.text(xx - 1.5, y1 + 0.9, name, ha="center", va="center", fontsize=7.2,
                fontweight="bold", color=colr, zorder=10,
                bbox=dict(boxstyle="round,pad=0.22", facecolor=BG,
                          edgecolor=colr, linewidth=0.8))

for label, _d, holes, _g, _c in PARTS:
    for h in holes:
        hx, hy = parse(h)
        ax.add_patch(patches.Circle((X(hx), hy), 0.34, facecolor="none",
                                    edgecolor=C_PIN, linewidth=1.5, zorder=8))
    hx, hy = parse(holes[0])
    ax.text(X(hx) + 0.75, hy, label, ha="left", va="center",
            fontsize=8.4, fontweight="bold", color=C_PIN, zorder=9)

ax.text(7.5, 22.0, "в столбце 09 строки M…Q НЕ паять — там разрыв между «+12 В отвод» и «затвор»",
        ha="center", va="center", fontsize=8.6, color=WARN, fontweight="bold", zorder=9)

# ------------------------------- ЗАГОЛОВОК ----------------------------------
fig.text(0.5, 0.968, "СИЛОВАЯ ПЛАТА МАГЛЕВ-СТЕНДА — РАСКЛАДКА НА ПЕРФОПЛАТЕ 14 × 20",
         ha="center", fontsize=19.5, fontweight="bold", color=TXT)
fig.text(0.5, 0.936,
         "5 вертикальных дорожек припоем снизу  •  одна перемычка сверху  •  "
         "силовая петля «конденсатор → катушка → ключ» замкнута накоротко",
         ha="center", fontsize=11, color=TXT_DIM)

legend = [(C_12V, "+12 В"), (C_GND, "GND"), (C_DRAIN, "сток / «−» катушки"),
          (C_GATE, "затвор"), (C_PIN, "выводы компонентов")]
x = 0.285
for colr, lbl in legend:
    fig.patches.append(plt.Rectangle((x, 0.9085), 0.017, 0.0055, color=colr,
                                     transform=fig.transFigure, figure=fig))
    fig.text(x + 0.022, 0.9112, lbl, fontsize=9, color=TXT_DIM, va="center")
    x += 0.093

if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    fig.savefig(os.path.join(here, "board_layout.png"), dpi=300,
                facecolor=BG, bbox_inches="tight", pad_inches=0.2)
    fig.savefig(os.path.join(here, "board_layout.svg"),
                facecolor=BG, bbox_inches="tight", pad_inches=0.2)
    print("saved: board_layout.png, board_layout.svg")
