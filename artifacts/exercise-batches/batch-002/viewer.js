import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {attachHeatField} from '../../chaturanga-heatmap/heat-field.js';
import {createHeatMaterial} from '../../chaturanga-heatmap/heat-material.js';

async function main() {
 const config = JSON.parse(document.querySelector('#heat-data').textContent);
 const stage = document.querySelector('#stage'), canvas = document.querySelector('canvas');
 function describe(item) {
  document.querySelector('#exercise-title').textContent = item.title;
  document.querySelector('#exercise-description').textContent = item.description;
  document.querySelector('#movement-note').textContent = item.note;
  document.querySelector('#main-zone').textContent = item.mainLabel;
  document.querySelector('#additional-zone').textContent = item.additionalLabel;
  document.querySelector('#legend').dataset.mode = item.displayMode;
  canvas.setAttribute('aria-label', item.title + ' · живая 3D-анимация с мягкими зонами мышц');
 }
 describe(config.exercises[0]);
 document.querySelector('#view').value = config.exercises[0].displayMode === 'stretch' ? 'dual' : 'front';
 for (const item of config.exercises) {
  const button = document.createElement('button'); button.type = 'button'; button.dataset.id = item.id;
  button.textContent = item.shortTitle; button.disabled = true;
  button.setAttribute('aria-pressed', String(item.id === config.exercises[0].id));
  button.onclick = () => select(item.id); document.querySelector('#exercises').append(button);
 }
 const renderer = new THREE.WebGLRenderer({canvas, alpha: true, antialias: true, preserveDrawingBuffer: true});
 renderer.setPixelRatio(Math.min(devicePixelRatio, 2)); renderer.setClearColor(0x000000, 0);
 renderer.shadowMap.enabled = false; renderer.outputColorSpace = THREE.SRGBColorSpace;
 const loader = new GLTFLoader();
 const gltf = config.model ? await loader.parseAsync(Uint8Array.from(atob(config.model), c => c.charCodeAt(0)).buffer, '')
  : await loader.loadAsync(config.modelUrl);
 const scene = new THREE.Scene(); scene.add(gltf.scene, new THREE.AmbientLight(0xffffff, 2.5));
 const light = new THREE.DirectionalLight(0xffffff, 1); light.position.set(1, 3, 5); scene.add(light);
 const {material, uniforms} = createHeatMaterial(), meshes = [], bones = new Map(), fieldCache = new Map();
 gltf.scene.traverse(object => {
  if (object.isBone) bones.set(object.name, object);
  if (!object.isMesh) return;
  meshes.push(object);
  for (const old of Array.isArray(object.material) ? object.material : [object.material]) {old.map?.dispose(); old.dispose();}
  object.material = material; object.castShadow = false; object.receiveShadow = false;
 });
 for (const exercise of config.exercises) {
  const fields = meshes.map(mesh => {
   const field = attachHeatField(mesh, {...config, ...exercise});
   return {field, attribute: mesh.geometry.getAttribute('heatZone')};
  });
  fieldCache.set(exercise.id, fields);
 }
 const cameras = [0, 1].map(() => new THREE.OrthographicCamera(-1, 1, 1, -1, .01, 30));
 const toThree = ([x, y, z]) => new THREE.Vector3(x, z, -y);
 const controls = new OrbitControls(cameras[0], canvas);
 controls.enablePan = false; controls.enableDamping = false; controls.minZoom = .65; controls.maxZoom = 2.8;
 const mixer = new THREE.AnimationMixer(gltf.scene);
 let exercise, clip, action, fields, linked, entries = [], mode = 'front', time = 0, playing = true, last = performance.now(), poseUpdates = 0;
 function render() {
  renderer.setScissorTest(false); renderer.clear(true, true, true); renderer.setScissorTest(true);
  for (const entry of entries) {
   renderer.setViewport(entry.x, entry.y, entry.width, entry.height);
   renderer.setScissor(entry.x, entry.y, entry.width, entry.height); renderer.render(scene, entry.camera);
  }
  renderer.setScissorTest(false);
 }
 function layout() {
  if (!exercise) return;
  const width = Math.max(240, stage.clientWidth), dual = mode === 'dual', stacked = dual && width < 540;
  const panelWidth = dual && !stacked ? (width - 12) / 2 : width;
  const panelHeight = Math.round(panelWidth / 1.65), height = stacked ? panelHeight * 2 + 12 : panelHeight;
  renderer.setSize(width, height, false); canvas.style.height = height + 'px';
  const chosen = dual ? [0, 1] : [mode === 'front' ? 0 : 1];
  entries = chosen.map((index, position) => {
   const camera = cameras[index], halfWidth = exercise.cameras[index].scale / 2;
   camera.left = -halfWidth; camera.right = halfWidth;
   camera.top = halfWidth / (panelWidth / panelHeight); camera.bottom = -camera.top; camera.updateProjectionMatrix();
   return {camera, width: panelWidth, height: panelHeight, x: stacked ? 0 : position * (panelWidth + 12),
    y: stacked ? (position === 0 ? panelHeight + 12 : 0) : 0};
  });
  render();
 }
 function reset() {
  linked = null;
  exercise.cameras.forEach((preset, index) => {
   cameras[index].position.copy(toThree(preset.position)); cameras[index].zoom = 1;
   cameras[index].lookAt(toThree(preset.target)); cameras[index].updateProjectionMatrix();
  });
  const index = mode === 'back' ? 1 : 0;
  controls.object = cameras[index]; controls.target.copy(toThree(exercise.cameras[index].target)); controls.update();
  if (mode === 'dual') linked = {rotation: cameras[0].quaternion.clone(), target: toThree(exercise.cameras[1].target),
   offset: cameras[1].position.clone().sub(toThree(exercise.cameras[1].target))};
  layout();
 }
 function pose(value) {
  time = Math.max(0, Math.min(clip.duration, value));
  action.paused = false; action.enabled = true; mixer.setTime(time); scene.updateMatrixWorld(true); poseUpdates++;
  // Stable training-emphasis zones; no invented phase-dependent activation model.
  uniforms.heatPhase.value = 1;
  const phase = exercise.phases.find(phase => time >= phase.start && time < phase.end) ?? exercise.phases.at(-1);
  document.querySelector('#phase').textContent = phase?.label ?? 'Движение';
  document.querySelector('#timeline').value = String(time); render();
 }
 function select(id) {
  exercise = config.exercises.find(item => item.id === id);
  if (!exercise) throw Error('Unknown exercise: ' + id);
  clip = gltf.animations.find(item => item.name === 'Exercise_' + id);
  if (!clip) throw Error('Animation is missing: ' + id);
  mixer.stopAllAction(); action = mixer.clipAction(clip).reset().setLoop(THREE.LoopOnce, 1);
  action.clampWhenFinished = true; action.play();
  fields = fieldCache.get(id);
  meshes.forEach((mesh, index) => mesh.geometry.setAttribute('heatZone', fields[index].attribute));
  const palette = exercise.displayMode === 'stretch' ? ['#72b4cf', '#2297c3', '#b1f2f3'] : ['#f7a64b', '#f24720', '#ffe09a'];
  ['heatAmber', 'heatRed', 'heatCore'].forEach((name, i) => uniforms[name].value.set(palette[i]));
  describe(exercise);
  mode = exercise.displayMode === 'stretch' ? 'dual' : 'front';
  document.querySelector('#view').value = mode;
  document.querySelector('#timeline').max = String(clip.duration);
  document.querySelectorAll('#exercises button').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.id === id)));
  playing = true; document.querySelector('#play').textContent = 'Пауза';
  reset(); pose(0);
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
 document.querySelector('#timeline').oninput = event => {playing = false; document.querySelector('#play').textContent = 'Продолжить'; pose(Number(event.target.value));};
 new ResizeObserver(layout).observe(stage);
 select(config.exercises[0].id); document.querySelector('#loading').hidden = true; document.querySelector('#poster')?.remove();
 document.querySelectorAll('#exercises button').forEach(button => {button.disabled = false;});
 window.heatReady = true; window.heatSelect = select;
 window.heatFrame = value => {playing = false; document.querySelector('#play').textContent = 'Продолжить'; pose(value);};
 window.heatProbe = () => {
  const gl = renderer.getContext(), pixel = new Uint8Array(4); gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, pixel);
  return {exerciseId: exercise.id, time, playing, duration: clip.duration, action: clip.name, mode, displayMode: exercise.displayMode,
   viewportCount: entries.length, cameras: cameras.map(camera => ({position: camera.position.toArray(), zoom: camera.zoom})),
   panEnabled: controls.enablePan, heatEnabled: uniforms.heatEnabled.value, heatPhase: uniforms.heatPhase.value,
   heatStrength: uniforms.heatStrength.value, meshes: meshes.length, bones: bones.size, poseUpdates,
   colorTextures: material.map ? 1 : 0, ao: !!material.aoMap, shadows: renderer.shadowMap.enabled,
   transparentCanvas: renderer.getContextAttributes().alpha && scene.background === null, cornerAlpha: pixel[3],
   sourceVertices: fields[0].field.sourceVertexCount, primary: Array.from(fields[0].field.primary), secondary: Array.from(fields[0].field.secondary),
   joints: Object.fromEntries([...bones].map(([name, bone]) => [name, bone.getWorldPosition(new THREE.Vector3()).toArray()]))};
 };
 // Actual skinned GLB surface positions, indexed by the original Blender vertices.
 window.heatSurface = ids => {
  const result = {}, point = new THREE.Vector3();
  for (const mesh of meshes) {
   const source = mesh.geometry.getAttribute('_source_index'); mesh.skeleton.update();
   for (let i = 0; i < source.count; i++) {
    const id = Math.round(source.getX(i)); if (ids && !ids.includes(id)) continue;
    mesh.getVertexPosition(i, point); mesh.localToWorld(point); result[id] = point.toArray();
   }
  }
  return result;
 };
 window.heatFrustum = () => entries.map(({camera}) => {
  const min = [Infinity, Infinity], max = [-Infinity, -Infinity], point = new THREE.Vector3();
  camera.updateMatrixWorld(true);
  for (const mesh of meshes) {
   mesh.skeleton.update();
   for (let i = 0; i < mesh.geometry.getAttribute('position').count; i++) {
    mesh.getVertexPosition(i, point); mesh.localToWorld(point); point.project(camera);
    for (const [axis, value] of [point.x, point.y].entries()) {min[axis] = Math.min(min[axis], value); max[axis] = Math.max(max[axis], value);}
   }
  }
  return {min, max};
 });
 function tick(now) {
  const delta = Math.min(.1, (now - last) / 1000); last = now;
  if (playing) pose((time + delta) % clip.duration);
  requestAnimationFrame(tick);
 }
 requestAnimationFrame(tick);
}
main().catch(error => {
 window.heatError = error.message; document.querySelector('#loading').textContent = 'Не удалось открыть 3D. ' + error.message;
 document.querySelector('#loading').hidden = false;
});
