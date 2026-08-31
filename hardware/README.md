# Hardware

| File | What |
|---|---|
| `bom.csv` | Bill of materials with procurement status per line |
| `../docs/figures/schematic.png` | Wiring schematic |
| `../docs/schematic.html` | The same schematic as a zoomable page with pin tables |
| `../docs/figures/board_layout.png` | Perfboard layout: top view and mirrored underside |
| `../docs/figures/interconnect.png` | Which subsystem connects to which, and with how many wires |
| `src/` | Generators for all of the above |

## Regenerating the figures

Every figure in this repository is generated from source, not drawn by hand,
so a design change cannot leave a stale diagram behind:

```bash
python3 src/draw_schematic.py    # -> schematic.png + .svg + .html
python3 src/board_layout.py      # -> board_layout.png + .svg
python3 src/interconnect.py      # -> interconnect.png + .svg
python3 src/annotate_bench.py    # -> annotated bench photo, EN and RU
```

Output paths are relative to the script, so run them from `hardware/src/` or
adjust the paths at the bottom of each file.

## Four rules that destroy hardware in seconds

| # | Rule | Consequence of breaking it |
|---|---|---|
| 1 | 1N5822 cathode stripe strictly to +12 V | diode conducts permanently, rail short, instant MOSFET failure |
| 2 | SS49E output only through a 10k/10k divider | sensor swings to 5 V, the S3 ADC pin tolerates 3.3 V |
| 3 | Analogue inputs only on ADC1 (GPIO 1–10) | ADC2 freezes when Wi-Fi is enabled |
| 4 | Never occupy GPIO 35/36/37 | octal PSRAM of the N16R8 module lives there |

## Build notes

The power stage is soldered on double-sided perfboard, 14 × 20 holes: five
vertical tracks on the underside, one jumper on top. Component lead pitches —
not the schematic — dictate the layout, and the tightest constraint is the
IRLZ44N, whose three leads land in adjacent holes and therefore fix the order
of the supply rails.

All grounds meet at a single point at the MOSFET source. Power and signal
returns run there as separate wires; a shared return converts the coil's
20 kHz current pulses into apparent sensor noise, which is then usually
misdiagnosed as a software problem.
