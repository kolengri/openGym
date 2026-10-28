import {chromium} from '../first-exercise-3d/runtime/node_modules/playwright-core/index.mjs';
import * as THREE from '../first-exercise-3d/runtime/node_modules/three/build/three.module.js';
import {homedir} from 'node:os';
import {readFile,writeFile,mkdir,readdir,unlink} from 'node:fs/promises';
const browser=await chromium.launch({executablePath:process.env.EXERCISE_CHROME||homedir()+'/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell',headless:true,args:['--use-angle=metal']});
try{
 const page=await browser.newPage({viewport:{width:728,height:1000},deviceScaleFactor:1});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(new URL('./motion-viewer.html',import.meta.url).href);await page.waitForFunction(()=>window.modelReady,undefined,{timeout:60000});const ready=await page.evaluate(()=>window.modelReady);if(ready.clips.length!==3)throw Error('Expected exactly three clips');
 const samples=JSON.parse(await readFile(new URL('./motion-samples.json',import.meta.url),'utf8'));const modelMatrix=new THREE.Matrix4().fromArray(ready.modelMatrix);const report={renderer:'Three.js',fps:30,clips:[],errors};
 await page.locator('canvas').screenshot({path:new URL('./revised-model.png',import.meta.url).pathname});
 for(const clip of ready.clips){
  const short=clip.name.replace('Athlete_','');await page.evaluate(name=>window.selectPreview(name),clip.name);const dir=new URL('./frames/'+short+'/',import.meta.url);await mkdir(dir,{recursive:true});for(const n of await readdir(dir))if(/^\d{4}\.png$/.test(n))await unlink(new URL(n,dir));
  const count=Math.round(clip.duration*30),probes=[];let maxJointError=0,maxPlantedDrift=0;
  console.log('Rendering '+short+': '+count+' frames');
  for(let i=0;i<count;i++){
   const frame=await page.evaluate(t=>({png:window.captureFrame(t),probe:window.motionProbe()}),i/30);await writeFile(new URL(String(i).padStart(4,'0')+'.png',dir),Buffer.from(frame.png,'base64'));probes.push(frame.probe);
   for(const side of ['Left','Right']){const field=side==='Left'?'leftFoot':'rightFoot',source=samples[clip.name][i],p=source.feet[side];const expected=new THREE.Vector3(p[0],p[2],-p[1]).applyMatrix4(modelMatrix);maxJointError=Math.max(maxJointError,expected.distanceTo(new THREE.Vector3(...frame.probe[field])));if(i>0&&!source.moving[side]&&!samples[clip.name][i-1].moving[side])maxPlantedDrift=Math.max(maxPlantedDrift,new THREE.Vector3(...probes[i-1][field]).distanceTo(new THREE.Vector3(...frame.probe[field])));}
   if(i%45===0)console.log(short+' frame '+i+'/'+count);
  }
  await page.evaluate(t=>window.renderFrame(t),Math.min(clip.duration/2,1.0));await page.locator('canvas').screenshot({path:new URL('./'+short+'-muscles.png',import.meta.url).pathname});
  await page.evaluate(t=>window.renderFrame(t),clip.duration-1e-6);const end=await page.evaluate(()=>window.motionProbe());const loopError=Math.max(...['leftFoot','rightFoot','root'].map(k=>new THREE.Vector3(...end[k]).distanceTo(new THREE.Vector3(...probes[0][k]))));
  if(maxJointError>.001||maxPlantedDrift>.001||loopError>.001)throw Error(JSON.stringify({clip:short,maxJointError,maxPlantedDrift,loopError}));
  report.clips.push({name:clip.name,duration:clip.duration,frames:count,maxJointErrorMeters:maxJointError,maxPlantedFootDriftMeters:maxPlantedDrift,loopErrorMeters:loopError});
 }
 await page.evaluate(()=>window.selectPreview(''));await page.locator('#muscles').check();if(!(await page.evaluate(()=>window.previewState())).muscles)throw Error('Muscle toggle failed');await page.locator('#muscles').uncheck();await page.locator('#shorts').fill('40');await page.locator('#shorts').dispatchEvent('input');if(Math.abs((await page.evaluate(()=>window.previewState())).shortsOpacity-.4)>.001)throw Error('Opacity slider failed');
 if(errors.length)throw Error(errors.join('\n'));report.ok=true;report.controls={muscles:true,shortsOpacity:true,clipSelection:true};await writeFile(new URL('./threejs-motion-report.json',import.meta.url),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
}finally{await browser.close();}
