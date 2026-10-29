import {chromium} from '../first-exercise-3d/runtime/node_modules/playwright-core/index.mjs';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {homedir} from 'node:os';
const root=new URL('./',import.meta.url),data=JSON.parse(await readFile(new URL('poses.json',root),'utf8'));
const browser=await chromium.launch({headless:true,executablePath:process.env.EXERCISE_CHROME||homedir()+'/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell'});
try{
 const page=await browser.newPage({viewport:{width:728,height:900},deviceScaleFactor:1}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(new URL('viewer.html',root).href);await page.waitForFunction(()=>window.svgDemo);
 const files=[];
 for(const [name,clip] of Object.entries(data.clips)){
  await page.evaluate(n=>window.svgDemo.select(n),name);
  const frames=[];
  for(let i=0;i<clip.frames.length;i++)frames.push(await page.evaluate(t=>{window.svgDemo.render(t);return window.svgDemo.paths();},i*clip.duration/(clip.frames.length-1)));
  await page.evaluate(()=>window.svgDemo.render(0));
  const exported=await page.locator('svg').evaluate((svg,{frames,duration})=>{
   const copy=svg.cloneNode(true),NS='http://www.w3.org/2000/svg';
   for(const path of copy.querySelectorAll('path'))for(const attribute of ['d','opacity']){
    const values=frames.map(f=>f[path.id][attribute]);
    if(new Set(values).size===1)continue;
    const animation=document.createElementNS(NS,'animate');animation.setAttribute('attributeName',attribute);animation.setAttribute('dur',duration+'s');animation.setAttribute('repeatCount','indefinite');animation.setAttribute('values',values.join(';'));path.append(animation);
   }
   copy.setAttribute('width','640');copy.setAttribute('height','610');copy.setAttribute('style','background:#fafbfc');
   return '<?xml version="1.0" encoding="UTF-8"?>\n'+copy.outerHTML;
  },{frames,duration:clip.duration});
  const file=name==='Athlete_LateralShuffle'?'5965-mannequin.svg':name.replace('Athlete_','')+'.svg';await writeFile(new URL(file,root),exported);files.push({file,bytes:Buffer.byteLength(exported),duration:clip.duration});
  await page.evaluate(t=>window.svgDemo.render(t),clip.duration/2);await page.locator('svg').screenshot({path:new URL(name+'-review.png',root).pathname});
 }
 await page.locator('#muscles').uncheck();const disabled=await page.locator('#LeftquadOuter').getAttribute('fill');if(disabled!=='#b8ccdb')throw Error('Muscle toggle failed');await page.locator('#muscles').check();
 await page.goto(new URL('5965-mannequin.svg',root).href);await page.evaluate(()=>document.documentElement.pauseAnimations());await mkdir(new URL('frames/',root),{recursive:true});
 const screenshots=[];
 for(let i=0;i<156;i++){
  await page.evaluate(t=>document.documentElement.setCurrentTime(t),i/30);
  const png=await page.locator('svg').screenshot({path:new URL('frames/'+String(i).padStart(4,'0')+'.png',root).pathname});
  if([0,45,90,155].includes(i))screenshots.push({frame:i,bytes:png.length});
 }
 if(errors.length)throw Error(errors.join('\n'));
 await writeFile(new URL('review.json',root),JSON.stringify({ok:true,renderer:'SVG / Chromium',source:'Independent vector paths and previously authored motion rig',clips:files,firstVideoFrames:156,fps:30,width:640,height:610,muscleToggle:true,standaloneSmilRendered:true,screenshots,errors},null,2));
 console.log(JSON.stringify({files,errors}));
}finally{await browser.close();}
