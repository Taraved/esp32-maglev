#!/usr/bin/env python3
"""
Собирает schematic.html: встраивает schematic.svg внутрь страницы вместе
со справочными таблицами. Файл получается автономным — его можно открыть
в браузере или отправить одним вложением.

Вызывается автоматически из draw_schematic.py, но работает и отдельно:
    /Users/master/Projects/venv/bin/python3 build_page.py
"""

import os
import re

PAGE = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Маглев-стенд · монтажная схема</title>
<style>
  :root {{
    --bg: #f6f7fb;  --panel: #ffffff;   --ink: #0f172a;   --muted: #5a6478;
    --line: #dfe4ee; --accent: #0369a1; --warn-bg: #fff7ed; --warn-line: #fdba74;
    --warn-ink: #9a3412; --code-bg: #eef1f7; --shadow: 0 1px 3px rgba(15,23,42,.07);
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --bg: #0b0f19; --panel: #131b2e; --ink: #e8edf7; --muted: #94a3b8;
      --line: #233554; --accent: #38bdf8; --warn-bg: #2a1a0c; --warn-line: #92400e;
      --warn-ink: #fcd34d; --code-bg: #0f1626; --shadow: none;
    }}
  }}
  :root[data-theme="dark"] {{
    --bg: #0b0f19; --panel: #131b2e; --ink: #e8edf7; --muted: #94a3b8;
    --line: #233554; --accent: #38bdf8; --warn-bg: #2a1a0c; --warn-line: #92400e;
    --warn-ink: #fcd34d; --code-bg: #0f1626; --shadow: none;
  }}

  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--bg); color: var(--ink);
    font: 15px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
          "Helvetica Neue", Arial, sans-serif;
    -webkit-text-size-adjust: 100%;
  }}
  .wrap {{ max-width: 1240px; margin: 0 auto; padding: 32px 20px 72px; }}

  header {{ margin-bottom: 28px; }}
  h1 {{ font-size: 26px; line-height: 1.25; margin: 0 0 6px; letter-spacing: -.01em; }}
  .sub {{ color: var(--muted); font-size: 14.5px; margin: 0; }}
  .meta {{ color: var(--muted); font-size: 13px; margin-top: 10px; }}

  h2 {{ font-size: 18px; margin: 40px 0 12px; letter-spacing: -.01em; }}
  h2:first-of-type {{ margin-top: 32px; }}

  .panel {{
    background: var(--panel); border: 1px solid var(--line);
    border-radius: 12px; box-shadow: var(--shadow); overflow: hidden;
  }}

  /* --- вьюер схемы --- */
  .toolbar {{
    display: flex; gap: 8px; align-items: center; flex-wrap: wrap;
    padding: 10px 12px; border-bottom: 1px solid var(--line);
  }}
  .toolbar button {{
    font: inherit; font-size: 13px; padding: 5px 12px; cursor: pointer;
    color: var(--ink); background: var(--bg); border: 1px solid var(--line);
    border-radius: 7px;
  }}
  .toolbar button:hover {{ border-color: var(--accent); color: var(--accent); }}
  .toolbar .hint {{ color: var(--muted); font-size: 12.5px; margin-left: auto; }}
  #stage {{
    overflow: hidden; background: #0b0f19; cursor: grab;
    height: min(74vh, 760px); touch-action: none;
  }}
  #stage.dragging {{ cursor: grabbing; }}
  #pan {{ transform-origin: 0 0; will-change: transform; }}
  #pan svg {{ display: block; width: 1894px; height: auto; }}

  /* --- таблицы --- */
  table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  th, td {{ text-align: left; padding: 9px 14px; border-bottom: 1px solid var(--line); }}
  th {{ font-size: 12px; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); font-weight: 600; }}
  tr:last-child td {{ border-bottom: none; }}
  td code, .mono {{
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 13px; background: var(--code-bg); padding: 1px 6px; border-radius: 5px;
  }}
  .scroller {{ overflow-x: auto; }}
  .dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 8px; vertical-align: -1px; }}

  .rules {{ list-style: none; margin: 0; padding: 0; }}
  .rules li {{
    padding: 12px 16px; border-bottom: 1px solid var(--line);
    display: grid; grid-template-columns: 26px 1fr; gap: 10px; align-items: start;
  }}
  .rules li:last-child {{ border-bottom: none; }}
  .rules b {{ color: var(--warn-ink); }}
  .num {{
    background: var(--warn-bg); border: 1px solid var(--warn-line); color: var(--warn-ink);
    border-radius: 6px; text-align: center; font-size: 12px; font-weight: 700;
    line-height: 20px; height: 22px;
  }}
  .cols {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
  footer {{ margin-top: 44px; color: var(--muted); font-size: 13px; }}
  a {{ color: var(--accent); }}
</style>
</head>
<body>

<div class="wrap">
  <header>
    <h1>Стенд магнитной левитации — монтажная схема</h1>
    <p class="sub">ESP32-S3-WROOM-1 N16R8 · силовой ключ IRLZ44N + 1N5822 ·
       дифференциальная пара SS49E · токовый монитор INA219 · рабочий зазор 2.5 мм</p>
    <p class="meta">Схема сгенерирована из <span class="mono">draw_schematic.py</span> ·
       описание проекта — <span class="mono">README.md</span> ·
       порядок сборки — <span class="mono">ASSEMBLY.md</span></p>
  </header>

  <div class="panel">
    <div class="toolbar">
      <button id="zin">увеличить</button>
      <button id="zout">уменьшить</button>
      <button id="fit">вписать</button>
      <button id="full">100 %</button>
      <span class="hint">колесо — масштаб, перетаскивание — сдвиг</span>
    </div>
    <div id="stage"><div id="pan">
{svg}
    </div></div>
  </div>

  <h2>Подключения к плате</h2>
  <div class="panel scroller">
    <table>
      <thead><tr><th>Сигнал</th><th>Пин</th><th>Куда идёт</th><th>Почему этот пин</th></tr></thead>
      <tbody>
        <tr><td><span class="dot" style="background:#06b6d4"></span>Датчик Холла A</td>
            <td><code>GPIO 4</code></td><td>средняя точка делителя A</td><td>ADC1_CH3</td></tr>
        <tr><td><span class="dot" style="background:#3b82f6"></span>Датчик Холла B</td>
            <td><code>GPIO 5</code></td><td>средняя точка делителя B</td><td>ADC1_CH4</td></tr>
        <tr><td><span class="dot" style="background:#eab308"></span>ШИМ на затвор</td>
            <td><code>GPIO 16</code></td><td>100 Ом → затвор IRLZ44N</td><td>LEDC, свободен, не strapping</td></tr>
        <tr><td><span class="dot" style="background:#a855f7"></span>I²C SDA</td>
            <td><code>GPIO 8</code></td><td>SDA модуля INA219</td><td>штатный SDA S3</td></tr>
        <tr><td><span class="dot" style="background:#e2e8f0"></span>I²C SCL</td>
            <td><code>GPIO 9</code></td><td>SCL модуля INA219</td><td>штатный SCL S3</td></tr>
        <tr><td><span class="dot" style="background:#22d3ee"></span>Метка времени</td>
            <td><code>GPIO 17</code></td><td>щуп осциллографа</td><td>замер времени шага регулятора</td></tr>
        <tr><td><span class="dot" style="background:#f97316"></span>Питание датчиков</td>
            <td><code>5V</code></td><td>VCC обоих SS49E</td><td>SS49E требует 4.5–6 В</td></tr>
        <tr><td><span class="dot" style="background:#10b981"></span>Логика INA219</td>
            <td><code>3V3</code></td><td>VCC модуля INA219</td><td>логика модуля</td></tr>
        <tr><td><span class="dot" style="background:#64748b"></span>Земля</td>
            <td><code>GND</code></td><td>звёздная земля у истока</td><td>единая опорная точка</td></tr>
      </tbody>
    </table>
  </div>
  <p class="meta">Ряд A определяется по первым трём контактам: <span class="mono">3V3 · 3V3 · RST</span>.
     Ряд B начинается с <span class="mono">GND · GND · 19</span>. Все сигналы проекта — на ряду A.</p>

  <div class="cols">
    <div>
      <h2>Что убьёт железо за секунды</h2>
      <div class="panel"><ul class="rules">
        <li><span class="num">1</span><span><b>Полоса 1N5822 (катод) — строго к +12 В.</b>
            Наоборот — диод открыт постоянно, КЗ по питанию, мгновенный пробой ключа.</span></li>
        <li><span class="num">2</span><span><b>Выход SS49E — только через делитель 10к/10к.</b>
            На выходе датчика до 5 В, вход АЦП терпит 3.3 В.</span></li>
        <li><span class="num">3</span><span><b>Аналог — только на ADC1 (GPIO 1–10).</b>
            ADC2 не работает при включённом Wi-Fi: показания замрут.</span></li>
        <li><span class="num">4</span><span><b>GPIO 35, 36, 37 не занимать.</b>
            Заняты octal PSRAM модуля N16R8.</span></li>
      </ul></div>
    </div>
    <div>
      <h2>Занятые и опасные пины</h2>
      <div class="panel scroller"><table>
        <thead><tr><th>Пины</th><th>Причина</th></tr></thead>
        <tbody>
          <tr><td><code>35 · 36 · 37</code></td><td>Octal PSRAM модуля N16R8</td></tr>
          <tr><td><code>19 · 20</code></td><td>Нативный USB (D− / D+)</td></tr>
          <tr><td><code>0 · 3 · 45 · 46</code></td><td>Strapping — влияют на режим загрузки</td></tr>
          <tr><td><code>43 · 44</code></td><td>UART отладочной консоли (RX/TX)</td></tr>
          <tr><td><code>11 … 20</code></td><td>ADC2 — глушится Wi-Fi (как выходы годятся)</td></tr>
        </tbody>
      </table></div>
    </div>
  </div>

  <h2>Звёздная земля</h2>
  <div class="panel scroller">
    <table>
      <thead><tr><th>№</th><th>Что сводится в точку у истока MOSFET</th></tr></thead>
      <tbody>
        <tr><td>1</td><td>Исток IRLZ44N</td></tr>
        <tr><td>2</td><td>«−» блока питания 12 В</td></tr>
        <tr><td>3</td><td>«−» электролитов 470 мкФ</td></tr>
        <tr><td>4</td><td>GND платы ESP32-S3</td></tr>
        <tr><td>5</td><td>Нижние выводы делителей</td></tr>
        <tr><td>6</td><td>GND датчиков Холла</td></tr>
        <tr><td>7</td><td>GND модуля INA219</td></tr>
      </tbody>
    </table>
  </div>
  <p class="meta">Силовая и сигнальная земля идут к этой точке разными проводами.
     Общий провод на две функции = импульсы тока катушки попадают в опорную точку АЦП.</p>

  <footer>
    Схема пересобирается командой <span class="mono">python3 draw_schematic.py</span> —
    она перезаписывает <span class="mono">schematic.png</span>,
    <span class="mono">schematic.svg</span> и эту страницу.
  </footer>
</div>

<script>
(function () {{
  var stage = document.getElementById('stage'), pan = document.getElementById('pan');
  var svg = pan.querySelector('svg');
  if (svg) {{ svg.removeAttribute('width'); svg.removeAttribute('height'); }}
  var W = 1894, H = 1102;                       // размеры холста схемы
  var s = 1, x = 0, y = 0;

  function apply() {{ pan.style.transform = 'translate(' + x + 'px,' + y + 'px) scale(' + s + ')'; }}
  function fit() {{
    var r = stage.getBoundingClientRect();
    s = Math.min(r.width / W, r.height / H);
    x = (r.width - W * s) / 2; y = (r.height - H * s) / 2;
    apply();
  }}
  function zoomAt(cx, cy, k) {{
    var ns = Math.max(0.1, Math.min(8, s * k));
    x = cx - (cx - x) * (ns / s); y = cy - (cy - y) * (ns / s);
    s = ns; apply();
  }}

  document.getElementById('zin').onclick  = function () {{ var r = stage.getBoundingClientRect(); zoomAt(r.width / 2, r.height / 2, 1.3); }};
  document.getElementById('zout').onclick = function () {{ var r = stage.getBoundingClientRect(); zoomAt(r.width / 2, r.height / 2, 1 / 1.3); }};
  document.getElementById('fit').onclick  = fit;
  document.getElementById('full').onclick = function () {{
    var r = stage.getBoundingClientRect();
    zoomAt(r.width / 2, r.height / 2, 1 / s);   // приводим масштаб ровно к 1:1
  }};

  stage.addEventListener('wheel', function (e) {{
    e.preventDefault();
    var r = stage.getBoundingClientRect();
    zoomAt(e.clientX - r.left, e.clientY - r.top, e.deltaY < 0 ? 1.12 : 1 / 1.12);
  }}, {{ passive: false }});

  var drag = null;
  stage.addEventListener('pointerdown', function (e) {{
    drag = {{ px: e.clientX, py: e.clientY }};
    stage.setPointerCapture(e.pointerId); stage.classList.add('dragging');
  }});
  stage.addEventListener('pointermove', function (e) {{
    if (!drag) return;
    x += e.clientX - drag.px; y += e.clientY - drag.py;
    drag.px = e.clientX; drag.py = e.clientY; apply();
  }});
  ['pointerup', 'pointercancel'].forEach(function (ev) {{
    stage.addEventListener(ev, function () {{ drag = null; stage.classList.remove('dragging'); }});
  }});

  window.addEventListener('resize', fit);
  fit();
}})();
</script>
</body>
</html>
"""


def build_html(here=None):
    here = here or os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "schematic.svg"), encoding="utf-8") as f:
        svg = f.read()
    # выбрасываем XML-пролог и DOCTYPE — внутри HTML они не нужны
    svg = svg[svg.index("<svg"):]
    # matplotlib не проставляет preserveAspectRatio, а нам нужна отзывчивость
    svg = re.sub(r'<svg ', '<svg preserveAspectRatio="xMidYMid meet" ', svg, count=1)
    out = os.path.join(here, "schematic.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(PAGE.format(svg=svg))
    print("saved: schematic.html")
    return out


if __name__ == "__main__":
    build_html()
