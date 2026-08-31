#!/usr/bin/env python3
"""
Annotated bench photograph / аннотированное фото стенда.

The rig has no levitation footage yet, so the single assembly photograph has
to carry more weight than a snapshot normally would: it is turned into a
labelled figure that lets a reader trace every subsystem and every wire.

Writes docs/figures/bench_annotated_en.jpg and bench_annotated_ru.jpg
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.image as mpimg

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "..", "..", "docs", "figures")
SRC = os.path.join(FIG, "bench_raw.jpg")

BG, INK, DIM = "#0b0f19", "#f8fafc", "#94a3b8"
C_MCU, C_SENSE, C_POWER, C_ACT, C_GND = "#38bdf8", "#a855f7", "#ef4444", "#f43f5e", "#94a3b8"
C_SIG, C_MISS = "#eab308", "#fb7185"

# Boxes and callouts in image fractions (x, y from top-left, w, h).
# Coordinates were read off the 4032x3024 original.
LABELS = {
    "en": [
        ("A", 0.187, 0.376, 0.126, 0.298, C_MCU,
         "ESP32-S3-DevKitC-1 (N16R8)", "control loop, 1 kHz on core 0", 0.030, 0.300),
        ("F", 0.230, 0.095, 0.350, 0.230, C_SIG,
         "PWM 20 kHz -> 100 ohm -> gate", "the only signal wire to the power board",
         0.120, 0.045),
        ("E", 0.638, 0.238, 0.082, 0.098, C_POWER,
         "IRLZ44N + heatsink", "logic-level: full turn-on from 3.3 V", 0.760, 0.150),
        ("D", 0.772, 0.448, 0.104, 0.145, C_ACT,
         "JF-XP25x20 electromagnet", "pot-core: usable gap only 2-3 mm", 0.870, 0.330),
        ("B", 0.399, 0.376, 0.138, 0.172, C_SENSE,
         "INA219 current monitor", "identification and logging, not in the loop",
         0.330, 0.690),
        ("C", 0.560, 0.299, 0.187, 0.348, C_POWER,
         "Power stage, soldered", "IRLZ44N + 1N5822 + 2 x 470 uF", 0.300, 0.800),
    ],
    "ru": [
        ("A", 0.187, 0.376, 0.126, 0.298, C_MCU,
         "ESP32-S3-DevKitC-1 (N16R8)", "контур управления 1 кГц на ядре 0", 0.030, 0.300),
        ("F", 0.230, 0.095, 0.350, 0.230, C_SIG,
         "ШИМ 20 кГц → 100 Ом → затвор", "единственный сигнальный провод на плату",
         0.120, 0.045),
        ("E", 0.638, 0.238, 0.082, 0.098, C_POWER,
         "IRLZ44N + радиатор", "logic-level: открывается от 3.3 В", 0.760, 0.150),
        ("D", 0.772, 0.448, 0.104, 0.145, C_ACT,
         "Электромагнит JF-XP25x20", "броневой: рабочий зазор всего 2–3 мм", 0.870, 0.330),
        ("B", 0.399, 0.376, 0.138, 0.172, C_SENSE,
         "Монитор тока INA219", "идентификация и логирование, вне контура",
         0.330, 0.690),
        ("C", 0.560, 0.299, 0.187, 0.348, C_POWER,
         "Силовая часть, пайка", "IRLZ44N + 1N5822 + 2 x 470 мкФ", 0.300, 0.800),
    ],
}

CAPTION = {
    "en": ("Assembly state, 31 Aug 2026. Every subsystem of the control chain is "
           "present and wired except the position sensor:\nthe differential SS49E "
           "pair and its bracket are the next build step, and without a position "
           "signal the loop cannot be closed."),
    "ru": ("Состояние сборки, 31 августа 2026. Собраны и соединены все узлы "
           "контура, кроме датчика положения:\nдифференциальная пара SS49E и её "
           "кронштейн — следующий шаг сборки, без сигнала положения контур "
           "замкнуть нельзя."),
}

MISSING = {
    "en": ("NOT YET BUILT: differential Hall pair (2x SS49E)\n"
           "mounts on a bracket at the magnet face, 5-8 mm off axis"),
    "ru": ("ЕЩЁ НЕ СОБРАНО: дифференциальная пара Холла (2x SS49E)\n"
           "ставится на кронштейн у торца магнита, 5–8 мм от оси"),
}

TITLE = {"en": "Fig. 1 — Magnetic levitation test bench, annotated",
         "ru": "Рис. 1 — Стенд магнитной левитации, аннотированное фото"}


def build(lang):
    img = mpimg.imread(SRC)
    h, w = img.shape[:2]
    fig_w = 16.0
    fig = plt.figure(figsize=(fig_w, fig_w * h / w * 1.30), dpi=150, facecolor=BG)

    ax = fig.add_axes([0.0, 0.155, 1.0, 0.775])
    ax.imshow(img)
    ax.set_xlim(0, w)
    ax.set_ylim(h, 0)
    ax.axis("off")

    for tag, x, y, bw, bh, col, title, sub, lx, ly in LABELS[lang]:
        ax.add_patch(patches.FancyBboxPatch(
            (x * w, y * h), bw * w, bh * h,
            boxstyle="round,pad=6,rounding_size=18",
            facecolor="none", edgecolor=col, linewidth=2.6, zorder=5))
        cx, cy = (x + bw / 2) * w, (y + bh / 2) * h
        tx, ty = lx * w, ly * h
        ax.annotate("", xy=(cx, cy), xytext=(tx, ty),
                    arrowprops=dict(arrowstyle="-", color=col, linewidth=1.6,
                                    alpha=0.85, shrinkA=2, shrinkB=2), zorder=6)
        ax.text(tx, ty, f"{tag}", ha="center", va="center", fontsize=13,
                fontweight="bold", color=BG, zorder=8,
                bbox=dict(boxstyle="circle,pad=0.38", facecolor=col, edgecolor="none"))
        ax.text(tx + 0.020 * w, ty - 0.011 * h, title, ha="left", va="center",
                fontsize=11.5, fontweight="bold", color=col, zorder=8,
                bbox=dict(boxstyle="round,pad=0.35", facecolor=BG,
                          edgecolor=col, linewidth=1.2))
        ax.text(tx + 0.020 * w, ty + 0.019 * h, sub, ha="left", va="center",
                fontsize=9.5, color=DIM, zorder=8,
                bbox=dict(boxstyle="round,pad=0.25", facecolor=BG, edgecolor="none"))

    # the missing subsystem, marked as missing rather than quietly omitted
    mx, my = 0.840 * w, 0.855 * h
    ax.add_patch(patches.FancyBboxPatch(
        (0.700 * w, 0.780 * h), 0.280 * w, 0.150 * h,
        boxstyle="round,pad=6,rounding_size=18", facecolor="none",
        edgecolor=C_MISS, linewidth=2.4, linestyle=(0, (7, 5)), zorder=5))
    ax.text(mx, my, MISSING[lang], ha="center", va="center", fontsize=10,
            color=C_MISS, fontweight="bold", zorder=8,
            bbox=dict(boxstyle="round,pad=0.4", facecolor=BG,
                      edgecolor=C_MISS, linewidth=1.3))

    fig.text(0.5, 0.955, TITLE[lang], ha="center", fontsize=17,
             fontweight="bold", color=INK)
    fig.text(0.5, 0.085, CAPTION[lang], ha="center", va="top", fontsize=11,
             color=DIM, linespacing=1.5)

    # JPEG, not PNG: this is a photograph with an overlay, and PNG costs
    # 6 MB per language for no visible benefit in a repository.
    out = os.path.join(FIG, f"bench_annotated_{lang}.jpg")
    fig.savefig(out, facecolor=BG, bbox_inches="tight", pad_inches=0.18,
                pil_kwargs={"quality": 88, "optimize": True})
    plt.close(fig)
    print("saved:", os.path.basename(out))


if __name__ == "__main__":
    for lg in ("en", "ru"):
        build(lg)
