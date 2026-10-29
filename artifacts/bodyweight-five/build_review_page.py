"""Package the five verified clips for offline review and download."""

import base64
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
CLIPS = [
    ("5965", "Приставные шаги", "Два приставных шага и возврат. Слева видны квадрицепсы и пресс, справа — икры и ягодицы."),
    ("5915", "Чатуранга на трёх опорах", "Левая нога поднята. Оба ракурса под углом: видны обе ладони на полу, грудь, трицепсы и ягодица."),
    ("5887", "Собака с поднятой ногой", "Левая нога поднимается, таз неподвижен. Голубым — растяжение опорной правой ноги; невыделенное тело однотонное."),
    ("0001", "Подъём корпуса на ¾", "Стопы на полу, колени согнуты, руки за головой. Слева движение сбоку, справа мышцы пресса."),
    ("9066", "Прыжки на одной ноге", "Сгибание колена, толчок носком, полёт и мягкое приземление на левую ногу. Дополнительный ракурс показывает икру и ягодицу."),
]

data = [dict(id=key, title=title, description=description,
             video="data:video/webm;base64," + base64.b64encode(
                 (ROOT / f"{key}-preview.webm").read_bytes()).decode())
        for key, title, description in CLIPS]
template = """<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Пять упражнений · анатомический манекен</title>
<style>
:root{color-scheme:light dark;--foreground:light-dark(#18232c,#eff3f6);--muted-foreground:light-dark(#53616e,#a8b5c1);--border:light-dark(#d4dce2,#465460);--secondary:light-dark(#e2edf2,#263f4d)}
*{box-sizing:border-box}body{margin:0;padding:8px 0;font:15px/1.5 system-ui,sans-serif;color:var(--foreground);background:transparent}
main{max-width:700px;margin:auto}h1{font-size:22px;line-height:1.25;margin:0 0 6px}p{margin:6px 0;color:var(--muted-foreground)}
nav{display:flex;gap:7px;flex-wrap:wrap;margin:16px 0 12px}button{font:inherit;font-size:13px;padding:8px 11px;border:1px solid var(--border);border-radius:8px;color:var(--foreground);background:transparent;cursor:pointer}
button[aria-pressed=true]{background:var(--secondary);border-color:var(--foreground)}button:focus-visible{outline:2px solid #4399d0;outline-offset:2px}
.stage{overflow:hidden;border-radius:10px;background:repeating-conic-gradient(#d7dce1 0% 25%,#f4f6f8 0% 50%) 0/24px 24px}
video{display:block;width:100%;height:auto;aspect-ratio:2;object-fit:contain;background:transparent}
.controls{display:flex;align-items:center;gap:12px;flex-wrap:wrap;font-size:13px;margin:10px 0}.controls select{font:inherit;padding:6px;color:var(--foreground);background:var(--secondary);border:1px solid var(--border);border-radius:6px}#seek{flex:1;min-width:90px}
h2{font-size:17px;margin:12px 0 3px}#description{min-height:48px}.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:13px;margin-top:14px}.legend span:before{content:"";display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;background:var(--color)}
.note{font-size:12px;margin-top:10px} @media(max-width:420px){body{padding:8px 0}h1{font-size:20px}#description{min-height:70px}}
</style></head><body><main>
<p>Два дополняющих ракурса · прозрачный фон · только выбранные мышцы</p>
<nav aria-label="Выбор упражнения"></nav>
<div class="stage"><video autoplay muted loop playsinline aria-label="Анимация упражнения"></video></div>
<div class="controls"><button id="play" type="button">Пауза</button><input id="seek" type="range" min="0" max="1" step="0.001" value="0" aria-label="Положение анимации"><label>Фон <select id="background"><option value="checker">Прозрачность</option><option value="white">Белый</option><option value="dark">Тёмный</option><option value="color">Цветной</option></select></label></div>
<h2 id="title"></h2><p id="description"></p>
<div class="legend"><span style="--color:#ed4035">Основная нагрузка</span><span style="--color:#f2ad32">Дополнительная</span><span style="--color:#42becb">Растяжение</span></div>
<p class="note">Цвет обозначает выбранные мышечные зоны упражнения. Это схематичная подсветка, а не измерение сокращения. Для оценки деталей скачайте видео в полном качестве.</p>
</main><script>
const clips=__CLIPS__;const nav=document.querySelector('nav'),video=document.querySelector('video');
function select(index){const clip=clips[index];video.src=clip.video;video.load();document.querySelector('#title').textContent=clip.title;document.querySelector('#description').textContent=clip.description;[...nav.children].forEach((button,i)=>button.setAttribute('aria-pressed',String(i===index)));video.play().catch(()=>{});window.selectedClip=clip.id;document.querySelector('#play').textContent='Пауза';}
document.querySelector('#background').onchange=e=>{document.querySelector('.stage').style.background=({checker:'',white:'#fff',dark:'#101925',color:'#593a76'})[e.target.value];};
document.querySelector('#play').onclick=()=>{if(video.paused){video.play();document.querySelector('#play').textContent='Пауза';}else{video.pause();document.querySelector('#play').textContent='Проиграть';}};
document.querySelector('#seek').oninput=e=>{if(Number.isFinite(video.duration)){video.pause();video.currentTime=Number(e.target.value)*video.duration;document.querySelector('#play').textContent='Проиграть';}};
video.ontimeupdate=()=>{if(video.duration)document.querySelector('#seek').value=String(video.currentTime/video.duration);};
clips.forEach((clip,i)=>{const button=document.createElement('button');button.type='button';button.textContent=(i+1)+'. '+clip.title;button.addEventListener('click',()=>select(i));nav.append(button)});select(0);
</script></body></html>
"""
html = template.replace("__CLIPS__", json.dumps(data, ensure_ascii=False))
(ROOT / "viewer.html").write_text(html)
assert len(html.encode()) < 512_000

with zipfile.ZipFile(ROOT / "five-bodyweight-animations.zip", "w",
                     compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for name in [f"{key}.{extension}" for key, _, _ in CLIPS for extension in ['webm','mp4']] + ["README.md", "clips.json", "camera-presets.json"]:
        info = zipfile.ZipInfo(name, date_time=(2026, 10, 28, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, (ROOT / name).read_bytes())
with zipfile.ZipFile(ROOT / "threejs-asset.zip", "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for name in ['bodyweight-five.glb','runtime-muscles.json','camera-presets.json','clips.json','README.md'] + [f'web-textures/{key}.png' for key in ['neutral']+[c[0] for c in CLIPS]]:
        info=zipfile.ZipInfo(name,date_time=(2026,10,28,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
        archive.writestr(info,(ROOT/name).read_bytes())
print(json.dumps({"html_bytes": len(html.encode()),
                  "archive_bytes": (ROOT / "five-bodyweight-animations.zip").stat().st_size,
                  "clips": [c[0] for c in CLIPS]}))
