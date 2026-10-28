import {build} from '../first-exercise-3d/runtime/node_modules/esbuild/lib/main.js';
import {readFile, writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';

const root = new URL('./', import.meta.url);
const runtime = fileURLToPath(new URL('../first-exercise-3d/runtime/node_modules', root));
const bundle = await build({entryPoints: [fileURLToPath(new URL('runtime_viewer.js', root))], bundle: true, write: false, format: 'iife', nodePaths: [runtime], minify: true});
const cameraPresets = JSON.parse(await readFile(new URL('camera-presets.json', root), 'utf8'));
const ids = ['5965', '5915', '5887', '0001', '9066'];
for (const id of ids) {
 if (!Array.isArray(cameraPresets[id]) || cameraPresets[id].length !== 2) throw Error('Expected two complementary camera presets for ' + id);
 for (const camera of cameraPresets[id]) {
  if (!camera.label || !Number.isFinite(camera.scale) || camera.scale <= 0 || ![camera.position, camera.target].every(vector => Array.isArray(vector) && vector.length === 3 && vector.every(Number.isFinite))) throw Error('Invalid camera preset for ' + id);
 }
}
const textures = {};
for (const id of ['neutral', ...ids]) textures[id] = (await readFile(new URL('web-textures/' + id + '.png', root))).toString('base64');
const data = {model: (await readFile(new URL('bodyweight-five.glb', root))).toString('base64'), textures, cameraPresets};
const html = `<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Пять упражнений — 3D-модель</title>
<style>
body{font:16px system-ui;margin:24px;color:#24303c;background:#fff}main{max-width:1296px;margin:auto}nav{display:flex;gap:12px;flex-wrap:wrap;align-items:center}select,button{font:inherit;padding:8px}p{line-height:1.5}input[type=range]{display:block;width:100%;margin:16px 0}canvas{display:block;width:100%;height:auto;background:transparent}.viewer-stage{margin:16px auto;width:100%;overflow:hidden}.viewer-stage[data-layout=single]{max-width:640px}.viewer-stage[data-background=white]{background:#fff}.viewer-stage[data-background=dark]{background:#202730}.viewer-stage[data-background=checker]{background-color:#fff;background-image:linear-gradient(45deg,#cbd1d6 25%,transparent 25%),linear-gradient(-45deg,#cbd1d6 25%,transparent 25%),linear-gradient(45deg,transparent 75%,#cbd1d6 75%),linear-gradient(-45deg,transparent 75%,#cbd1d6 75%);background-size:24px 24px;background-position:0 0,0 12px,12px -12px,-12px 0}#view-labels{display:flex;gap:16px;text-align:center;margin:16px 0 0;font-size:14px}#view-labels span{flex:1}button:focus-visible,select:focus-visible,input:focus-visible{outline:2px solid #1875b5;outline-offset:3px}
</style>
<main><nav>
<label>Упражнение <select id="clip"><option value="5965">1–2 stick drill</option><option value="5915">Трёхопорная чатуранга</option><option value="5887">Собака с поднятой ногой</option><option value="0001">3/4 sit-up</option><option value="9066">Прыжки в четырёх направлениях</option></select></label>
<label>Ракурс <select id="view"><option value="default">Два рекомендуемых ракурса</option><option value="primary">Основной</option><option value="detail">Дополнительный</option><option value="side">Сбоку</option><option value="front">Спереди</option><option value="back">Сзади</option><option value="muscles">Мышцы пресса</option></select></label>
<label>Фон <select id="background"><option value="white">Белый</option><option value="dark">Тёмный</option><option value="checker">Шахматный</option></select></label>
<label><input id="highlight" type="checkbox" checked>Подсветка</label><button id="play">Пауза</button><button id="reset-view">Вернуть ракурс</button></nav>
<div id="view-labels" aria-live="polite"></div><div id="stage" class="viewer-stage" data-layout="dual" data-background="white"><canvas width="1296" height="640" aria-label="Синхронные ракурсы 3D-упражнения"></canvas></div>
<input id="timeline" type="range" min="0" max="4" step="0.001" value="0" aria-label="Положение анимации">
<p>При открытии — рекомендуемые ракурсы. Проведите пальцем или мышью, чтобы повернуть модель в обоих видах; щипок двумя пальцами меняет масштаб. «Вернуть ракурс» восстанавливает исходный вид. Анимация продолжается при вращении. Красный — основная нагрузка, янтарный — дополнительные мышцы, голубой — растяжение. Это иллюстративная карта. Тени и AO отключены.</p><p id="status" role="status"></p>
</main><script id="runtime-data" type="application/json">${JSON.stringify(data)}</script><script>${bundle.outputFiles[0].text}</script></html>`;
await writeFile(new URL('threejs-viewer.html', root), html);
console.log('Built self-contained transparent dual-view Three.js viewer:', Buffer.byteLength(html), 'bytes');
