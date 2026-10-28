import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';

async function main() {
 const config = JSON.parse(document.querySelector('#runtime-data').textContent);
 const loader = new GLTFLoader();
 const gltf = config.modelUrl
  ? await loader.loadAsync(config.modelUrl)
  : await loader.parseAsync(Uint8Array.from(atob(config.model), character => character.charCodeAt(0)).buffer, '');
 const canvas = document.querySelector('canvas');
 const stage = document.querySelector('#stage');
 const renderer = new THREE.WebGLRenderer({canvas, alpha: true, antialias: true, preserveDrawingBuffer: true});
 renderer.setPixelRatio(1);
 renderer.setClearColor(0x000000, 0);
 renderer.autoClear = false;
 renderer.shadowMap.enabled = false;
 renderer.outputColorSpace = THREE.SRGBColorSpace;
 renderer.toneMapping = THREE.NeutralToneMapping;
 const scene = new THREE.Scene();
 scene.background = null;
 scene.add(gltf.scene);
 scene.add(new THREE.AmbientLight(0xffffff, 2.5));
 const key = new THREE.DirectionalLight(0xffffff, 1.25);
 key.position.set(1, 3, 5);
 key.castShadow = false;
 scene.add(key);
 const meshes = [], bones = new Map(), skeletons = new Set();
 const materials = () => meshes.flatMap(mesh => Array.isArray(mesh.material) ? mesh.material : [mesh.material]);
 gltf.scene.traverse(object => {
  if (object.isBone) bones.set(object.name, object);
  if (object.isMesh) {
   meshes.push(object);
   if (object.skeleton) skeletons.add(object.skeleton);
   object.castShadow = false;
   object.receiveShadow = false;
  }
 });
 for (const material of materials()) {
  material.aoMap = null;
  material.roughness = .95;
  material.metalness = 0;
 }
 const textureLoader = new THREE.TextureLoader();
 const atlasUvChannel = materials()[0].map?.channel ?? 0;
 const importedMaps = new Set(materials().map(material => material.map).filter(Boolean));
 async function loadTexture(id) {
  const source = config.textureUrls?.[id] || (config.textures?.[id] ? 'data:image/png;base64,' + config.textures[id] : null);
  if (!source) throw Error('Missing activation texture: ' + id);
  const texture = await textureLoader.loadAsync(source);
  texture.flipY = false;
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.channel = atlasUvChannel;
  return texture;
 }
 const neutralTexture = await loadTexture('neutral');
 let activeTexture = null, activeTextureId = null, textureRequest = 0, textureLoading = false;
 const makeCamera = () => new THREE.OrthographicCamera(-1.1, 1.1, 1.1, -1.1, .01, 30);
 const recommendedCameras = [makeCamera(), makeCamera()];
 const camera = makeCamera();
 const controls = new OrbitControls(camera, canvas);
 controls.enablePan = false;
 controls.enableDamping = false;
 const mixer = new THREE.AnimationMixer(gltf.scene);
 const clips = new Map(gltf.animations.map(clip => [clip.name, clip]));
 let selected = '5965', time = 0, playing = true, highlight = true, last = performance.now();
 let viewMode = 'default', viewportEntries = [], poseEvaluations = 0, lastRenderCalls = 0;
 const toThree = ([x, y, z]) => [x, z, -y];
 function configureCamera(targetCamera, preset) {
  targetCamera.left = targetCamera.bottom = -preset.scale / 2;
  targetCamera.right = targetCamera.top = preset.scale / 2;
  targetCamera.updateProjectionMatrix();
  targetCamera.position.set(...preset.position);
  targetCamera.lookAt(...preset.target);
 }
 function presets() {
  const shots = config.cameraPresets[selected];
  if (!Array.isArray(shots) || shots.length !== 2) throw Error('Missing complementary cameras for ' + selected);
  return shots.map(shot => ({...shot, position: toThree(shot.position), target: toThree(shot.target)}));
 }
 function renderViews() {
  renderer.setScissorTest(false);
  renderer.setViewport(0, 0, canvas.width, canvas.height);
  renderer.clear(true, true, true);
  renderer.setScissorTest(true);
  lastRenderCalls = 0;
  for (const viewport of viewportEntries) {
   renderer.setViewport(viewport.x, 0, viewport.width, 640);
   renderer.setScissor(viewport.x, 0, viewport.width, 640);
   renderer.render(scene, viewport.camera);
   lastRenderCalls++;
  }
  renderer.setScissorTest(false);
  renderer.setViewport(0, 0, canvas.width, canvas.height);
 }
 function view(kind = 'default') {
  viewMode = kind;
  const shots = presets();
  shots.forEach((shot, index) => configureCamera(recommendedCameras[index], shot));
  const dual = kind === 'default';
  stage.dataset.layout = dual ? 'dual' : 'single';
  renderer.setSize(dual ? 1296 : 640, 640, false);
  controls.enabled = !dual;
  if (dual) {
   viewportEntries = recommendedCameras.map((shotCamera, index) => ({camera: shotCamera, x: index * 656, width: 640}));
  } else {
   let shot;
   if (kind === 'primary' || kind === 'detail') shot = shots[kind === 'primary' ? 0 : 1];
   else if (kind === 'side') shot = {position: [6, .9, 0], target: [0, .9, 0], scale: 2.2};
   else if (kind === 'back') shot = {position: [0, .9, -6], target: [0, .9, 0], scale: 2.2};
   else if (kind === 'muscles') shot = {position: [0, 4.5, 3.5], target: [0, .35, .05], scale: 1.95};
   else shot = {position: [0, .9, 6], target: [0, .9, 0], scale: 2.2};
   configureCamera(camera, shot);
   controls.target.set(...shot.target);
   controls.update();
   viewportEntries = [{camera, x: 0, width: 640}];
  }
  const labels = dual ? shots.map(shot => shot.label) : [kind === 'primary' ? shots[0].label : kind === 'detail' ? shots[1].label : document.querySelector('#view').selectedOptions[0].textContent];
  document.querySelector('#view-labels').replaceChildren(...labels.map(label => {
   const span = document.createElement('span');
   span.textContent = label;
   return span;
  }));
  renderViews();
 }
 function material() {
  for (const item of materials()) {
   item.map = highlight && activeTextureId === selected ? activeTexture : neutralTexture;
   item.needsUpdate = true;
  }
  for (const texture of importedMaps) texture.dispose();
  importedMaps.clear();
 }
 function pose(value) {
  time = Math.max(0, Math.min(value, clips.get('Exercise_' + selected).duration));
  mixer.setTime(time);
  poseEvaluations++;
  scene.updateMatrixWorld(true);
  renderViews();
  document.querySelector('#timeline').value = String(time);
 }
 async function select(id) {
  if (!clips.has('Exercise_' + id)) throw Error('Unknown exercise clip: ' + id);
  const request = ++textureRequest;
  const previousTexture = activeTexture;
  activeTexture = null;
  activeTextureId = null;
  textureLoading = true;
  mixer.stopAllAction();
  selected = id;
  const action = mixer.clipAction(clips.get('Exercise_' + id));
  action.reset().setLoop(THREE.LoopOnce, 1);
  action.clampWhenFinished = true;
  action.play();
  time = 0;
  document.querySelector('#clip').value = id;
  document.querySelector('#view').value = 'default';
  document.querySelector('#timeline').max = String(clips.get('Exercise_' + id).duration);
  material();
  previousTexture?.dispose();
  view();
  pose(0);
  let texture;
  try {
   texture = await loadTexture(id);
  } catch (error) {
   if (request === textureRequest) {textureLoading = false; throw error;}
   return;
  }
  if (request !== textureRequest) {texture.dispose(); return;}
  activeTexture = texture;
  activeTextureId = id;
  textureLoading = false;
  material();
  renderViews();
 }
 function setBackground(value) {
  if (!['white', 'dark', 'checker'].includes(value)) throw Error('Unknown backdrop: ' + value);
  stage.dataset.background = value;
 }
 function setPlaying(value) {
  playing = value;
  document.querySelector('#play').textContent = playing ? 'Пауза' : 'Проиграть';
 }
 document.querySelector('#clip').onchange = event => select(event.target.value).catch(showError);
 document.querySelector('#view').onchange = event => view(event.target.value);
 document.querySelector('#background').onchange = event => setBackground(event.target.value);
 document.querySelector('#highlight').onchange = event => {highlight = event.target.checked; material(); renderViews();};
 document.querySelector('#play').onclick = () => setPlaying(!playing);
 document.querySelector('#timeline').oninput = event => {setPlaying(false); pose(Number(event.target.value));};
 controls.addEventListener('change', renderViews);
 window.setRuntimeClip = id => {setPlaying(false); return select(id);};
 window.renderRuntimeFrame = value => {setPlaying(false); pose(value);};
 window.runtimeProbe = () => {
  const gl = renderer.getContext(), pixel = new Uint8Array(4);
  const corners = [[0, 0], [canvas.width - 1, 0], [0, canvas.height - 1], [canvas.width - 1, canvas.height - 1]];
  const cornerAlpha = corners.map(([x, y]) => {gl.readPixels(x, y, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, pixel); return pixel[3];});
  return {
   joints: Object.fromEntries([...bones].map(([name, bone]) => [name, bone.getWorldPosition(new THREE.Vector3()).toArray()])),
   shadowMap: renderer.shadowMap.enabled, castShadow: meshes.some(mesh => mesh.castShadow), receiveShadow: meshes.some(mesh => mesh.receiveShadow),
   ao: materials().some(item => !!item.aoMap), sceneBackgroundNull: scene.background === null,
   contextAlpha: renderer.getContextAttributes().alpha, clearAlpha: renderer.getClearAlpha(), cornerAlpha,
   background: stage.dataset.background, cssBackground: getComputedStyle(stage).backgroundColor, cssBackgroundImage: getComputedStyle(stage).backgroundImage,
   canvasCssBackground: getComputedStyle(canvas).backgroundColor, viewMode, viewportCount: viewportEntries.length,
   viewportCameras: viewportEntries.map(entry => ({position: entry.camera.position.toArray(), width: entry.width, x: entry.x})),
   poseEvaluations, renderCalls: lastRenderCalls, modelInstances: scene.children.filter(child => child === gltf.scene).length,
   mixerRootIsModel: mixer.getRoot() === gltf.scene, orbitEnabled: controls.enabled,
   selected, activeTextureId, textureLoading, loadedTextureCount: 1 + Number(activeTexture !== null), gpuTextureCount: renderer.info.memory.textures,
   textureSize: [neutralTexture.image.width, neutralTexture.image.height],
   atlasUvChannel, materialUvChannels: [...new Set(materials().map(item => item.map.channel))]
  };
 };
 await select(selected);
 window.runtimeReady = {
  clips: gltf.animations.map(clip => ({name: clip.name, duration: clip.duration})), bones: bones.size, meshes: meshes.length,
  sourceIndexAttribute: meshes.every(mesh => !!mesh.geometry.getAttribute('_source_index')),
  skeletons: skeletons.size, defaultView: 'dual', cameraPresetIds: Object.keys(config.cameraPresets), textureBudget: '2 color textures plus skeleton data', atlasUvChannel
 };
 function tick(now) {
  const delta = Math.min(.1, (now - last) / 1000);
  last = now;
  if (playing) pose((time + delta) % clips.get('Exercise_' + selected).duration);
  else renderViews();
  requestAnimationFrame(tick);
 }
 requestAnimationFrame(tick);
}
function showError(error) {
 window.runtimeError = error.stack || error.message;
 document.querySelector('#status').textContent = error.message;
}
main().catch(showError);
