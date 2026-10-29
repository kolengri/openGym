"""Build a self-contained offline SVG review page without runtime dependencies."""
from pathlib import Path
P=Path(__file__).resolve().parent
html='''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>
body{margin:0;font:14px var(--font-sans,system-ui);color:var(--foreground,#222)}
.art{max-width:640px;background:#fafbfc;border-radius:16px;overflow:hidden}svg{display:block;width:100%;height:auto}.controls{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:12px 0}button,select{font:inherit;color:var(--foreground,#222);background:var(--secondary,#edf0f2);border:1px solid var(--border,#cdd2d7);padding:7px 10px;border-radius:8px}label{display:flex;gap:5px;align-items:center}#time{width:100%;max-width:520px}.legend{font-size:13px;color:var(--muted-foreground,#68717b);line-height:1.5}.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px;background:#ec574b}.dot.amber{background:#e3b453}
</style></head><body><div class="art"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 610" role="img" aria-label="Векторный манекен с подсветкой мышц"><defs><linearGradient id="mannequin" x1="0" x2="1" y1="0" y2=".25"><stop stop-color="#e0e6eb"/><stop offset=".5" stop-color="#d0d8df"/><stop offset="1" stop-color="#b6c1ca"/></linearGradient></defs></svg></div>
<div class="controls"><select id="clip" aria-label="Движение"><option value="Athlete_LateralShuffle">5965 · Приставные шаги</option><option value="Athlete_SquatPreview">Проба · Приседание</option><option value="Athlete_ArmRaisePreview">Проба · Подъём рук</option></select><button id="play">Пауза</button><label><input id="muscles" type="checkbox" checked>Мышцы</label></div>
<div class="controls"><span id="view-label"></span><span id="clock"></span></div><input id="time" aria-label="Положение анимации" type="range" min="0" max="5.2" step=".01" value="0">
<p class="legend"><span class="dot"></span>Выделенные мышцы　<span class="dot amber"></span>Стабилизаторы, включая пресс.<br><span id="zones"></span><br>Иллюстративная анатомия и деформация мышечных форм; это не измерение нагрузки.</p>
<script>window.poseData=POSE_DATA;</script><script>VIEWER_SOURCE</script></body></html>'''
html=html.replace('POSE_DATA',(P/'poses.json').read_text()).replace('VIEWER_SOURCE',(P/'viewer.js').read_text())
(P/'viewer.html').write_text(html)
print(f'Built {len(html.encode())} bytes')
