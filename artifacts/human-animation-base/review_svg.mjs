import {chromium} from '../first-exercise-3d/runtime/node_modules/playwright-core/index.mjs';
import {writeFile,mkdir} from 'node:fs/promises';
import {homedir} from 'node:os';
const P=new URL('./',import.meta.url),browser=await chromium.launch({headless:true,executablePath:process.env.EXERCISE_CHROME||homedir()+'/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell'});
try{
 const page=await browser.newPage({viewport:{width:640,height:640},deviceScaleFactor:1}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(new URL('human-squat.svg',P).href);await page.locator('svg').evaluate(e=>e.pauseAnimations());
 const out=new URL('svg-frames/',P);await mkdir(out,{recursive:true});const samples=[];
 for(let i=0;i<68;i++){
  const visible=await page.locator('svg').evaluate((svg,time)=>{svg.setCurrentTime(time);return [...svg.querySelectorAll(':scope > g')].filter(g=>getComputedStyle(g).visibility==='visible').map(g=>g.id);},i/30+.00001);
  if(visible.length!==1||visible[0]!=='frame'+i)throw Error('SVG visibility mismatch at '+i+': '+visible);
  await page.locator('svg').screenshot({path:new URL(String(i).padStart(4,'0')+'.png',out).pathname});
  if([0,34,67].includes(i)){await page.locator('svg').screenshot({path:new URL('svg-review-'+i+'.png',P).pathname});samples.push({frame:i,visible:visible[0]});}
 }
 if(errors.length)throw Error(errors.join('\n'));
 await writeFile(new URL('svg-review.json',P),JSON.stringify({ok:true,renderer:'Actual standalone animated SVG / Chromium',frames:68,fps:30,width:640,height:640,samples,oneVisibleFrameAtEverySample:true,errors},null,2));console.log('Reviewed all68 SVG frame states, no page errors.');
}finally{await browser.close();}
