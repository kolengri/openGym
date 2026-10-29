import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {attachHeatField} from './heat-field.js';
import {createHeatMaterial} from './heat-material.js';

async function main() {
 const config = JSON.parse(document.querySelector('#heat-data').textContent);
 const canvas = document.querySelector('canvas'), stage = document.querySelector('#stage');
 const renderer = new THREE.WebGLRenderer({canvas, alpha: true, antialias: true, preserveDrawingBuffer: true});
 renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
 renderer.setClearColor(0, 0); renderer.autoClear = false; renderer.shadowMap.enabled = false;
 renderer.toneMapping = THREE.NeutralToneMapping;
 const gltf = config.model
  ? await new GLTFLoader().parseAsync(Uint8Array.from(atob(config.model), character => character.charCodeAt(0)).buffer, '')
  : await new GLTFLoader().loadAsync(config.modelUrl);
 const scene = new THREE.Scene(); scene.add(gltf.scene);
 scene.add(new THREE.AmbientLight(0xffffff, 2.5));
 const key = new THREE.DirectionalLight(0xffffff, 1.0); key.position.set(1, 3, 5); scene.add(key);
 const {material, uniforms} = createHeatMaterial(), fields = [], meshes = [], bones = new Map();
 gltf.scene.traverse(object => {
  if (object.isBone) bones.set(object.name, object);
  if (!object.isMesh) return;
  fields.push(attachHeatField(object, config)); meshes.push(object);
  const previous = Array.isArray(object.material) ? object.material : [object.material];
  for (const item of previous) {item.map?.dispose(); item.dispose();}
  object.material = material; object.castShadow = false; object.receiveShadow = false;
 });
 const clip = gltf.animations.find(item => item.name === 'Exercise_5915');
 if (!clip) throw Error('Chaturanga animation is missing');
 const mixer = new THREE.AnimationMixer(gltf.scene);
 const action = mixer.clipAction(clip); action.setLoop(THREE.LoopOnce, 1); action.clampWhenFinished = true; action.play();
 const cameras = config.cameras.map(() => new THREE.OrthographicCamera(-1, 1, 1, -1, .01, 30));
 const toThree = ([x, y, z]) => new THREE.Vector3(x, z, -y);
 const controls = new OrbitControls(cameras[0], canvas);
 controls.enablePan = false; controls.enableDamping = false; controls.minZoom = .65; controls.maxZoom = 2.8;
 let linked = null, entries = [], mode = 'dual', time = 0, playing = true, last = performance.now(), poseUpdates = 0;
 function layout() {
  const width = Math.max(240, stage.clientWidth), dual = mode === 'dual', stacked = dual && width < 540;
  const panelWidth = dual && !stacked ? (width - 12) / 2 : width;
  const panelHeight = Math.round(panelWidth / 1.8), height = stacked ? panelHeight * 2 + 12 : panelHeight;
  renderer.setSize(width, height, false); canvas.style.height = height + 'px';
  const chosen = dual ? [0, 1] : [mode === 'front' ? 0 : 1];
  entries = chosen.map((index, position) => {
   const camera = cameras[index], halfWidth = config.cameras[index].scale / 2;
   camera.left = -halfWidth; camera.right = halfWidth; camera.top = halfWidth / (panelWidth / panelHeight); camera.bottom = -camera.top;
   camera.updateProjectionMatrix();
   return {camera, width: panelWidth, height: panelHeight, x: stacked ? 0 : position * (panelWidth + 12),
    y: stacked ? (position === 0 ? panelHeight + 12 : 0) : 0};
  });
  render();
 }
 function reset() {
  linked = null;
  config.cameras.forEach((preset, index) => {
   cameras[index].position.copy(toThree(preset.position)); cameras[index].zoom = 1;
   cameras[index].lookAt(toThree(preset.target)); cameras[index].updateProjectionMatrix();
  });
  const index = mode === 'back' ? 1 : 0;
  controls.object = cameras[index]; controls.target.copy(toThree(config.cameras[index].target)); controls.update();
  if (mode === 'dual') linked = {rotation: cameras[0].quaternion.clone(), target: toThree(config.cameras[1].target),
   offset: cameras[1].position.clone().sub(toThree(config.cameras[1].target))};
  layout();
 }
 function render() {
  renderer.setScissorTest(false); renderer.clear(true, true, true); renderer.setScissorTest(true);
  for (const entry of entries) {
   renderer.setViewport(entry.x, entry.y, entry.width, entry.height);
   renderer.setScissor(entry.x, entry.y, entry.width, entry.height); renderer.render(scene, entry.camera);
  }
  renderer.setScissorTest(false);
 }
 function pose(value) {
  time = Math.max(0, Math.min(clip.duration, value));
  action.paused = false; action.enabled = true; mixer.setTime(time); scene.updateMatrixWorld(true); poseUpdates++;
  const lower = .5 - .5 * Math.cos(2 * Math.PI * time / clip.duration);
  uniforms.heatPhase.value = .88 + .12 * lower;
  document.querySelector('#phase').textContent = lower < .04 ? 'Верхняя точка' : lower > .96 ? 'Нижняя точка' : time < clip.duration / 2 ? 'Опускание' : 'Подъём';
  document.querySelector('#timeline').value = String(time); render();
 }
 controls.addEventListener('change', () => {
  if (linked) {
   const rotation = cameras[0].quaternion.clone().multiply(linked.rotation.clone().invert());
   cameras[1].position.copy(linked.offset).applyQuaternion(rotation).add(linked.target);
   cameras[1].zoom = cameras[0].zoom; cameras[1].lookAt(linked.target); cameras[1].updateProjectionMatrix();
  }
  render();
 });
 document.querySelector('#play').onclick = () => {playing = !playing; document.querySelector('#play').textContent = playing ? 'Пауза' : 'Продолжить';};
 document.querySelector('#reset').onclick = reset;
 document.querySelector('#view').onchange = event => {mode = event.target.value; reset();};
 document.querySelector('#background').onchange = event => {stage.dataset.background = event.target.value;};
 document.querySelector('#zones').onchange = event => {uniforms.heatEnabled.value = Number(event.target.checked); render();};
 document.querySelector('#strength').oninput = event => {uniforms.heatStrength.value = Number(event.target.value); render();};
 document.querySelector('#timeline').max = String(clip.duration);
 document.querySelector('#timeline').oninput = event => {playing = false; document.querySelector('#play').textContent = 'Продолжить'; pose(Number(event.target.value));};
 new ResizeObserver(layout).observe(stage);
 reset(); pose(0);
 document.querySelector('#loading').hidden = true; document.querySelector('#poster')?.remove();
 window.heatReady = true;
 window.heatFrame = value => {playing = false; pose(value);};
 window.heatProbe = () => {
  const gl = renderer.getContext(), pixel = new Uint8Array(4); gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, pixel);
  return {time, playing, duration: clip.duration, action: clip.name, mode, viewportCount: entries.length,
   cameras: cameras.map(camera => ({position: camera.position.toArray(), zoom: camera.zoom})),
   panEnabled: controls.enablePan, heatEnabled: uniforms.heatEnabled.value, heatPhase: uniforms.heatPhase.value,
   heatStrength: uniforms.heatStrength.value, meshes: meshes.length, bones: bones.size, poseUpdates,
   colorTextures: material.map ? 1 : 0, ao: !!material.aoMap, shadows: renderer.shadowMap.enabled,
   transparentCanvas: renderer.getContextAttributes().alpha && scene.background === null,
   cornerAlpha: pixel[3], sourceVertices: fields[0].sourceVertexCount,
   primary: Array.from(fields[0].primary), secondary: Array.from(fields[0].secondary),
   joints: Object.fromEntries([...bones].map(([name, bone]) => [name, bone.getWorldPosition(new THREE.Vector3()).toArray()]))};
 };
 function tick(now) {
  const delta = Math.min(.1, (now - last) / 1000); last = now;
  if (playing) pose((time + delta) % clip.duration);
  requestAnimationFrame(tick);
 }
 requestAnimationFrame(tick);
}
main().catch(error => {
 window.heatError = error.message;
 document.querySelector('#loading').textContent = 'Не удалось открыть 3D. ' + error.message;
 document.querySelector('#loading').hidden = false;
});
