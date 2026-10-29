import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
import {chromium} from '../first-exercise-3d/runtime/node_modules/playwright-core/index.mjs';
import {homedir} from 'node:os';
const root=new URL('./',import.meta.url),presets=JSON.parse(await readFile(new URL('camera-presets.json',root)));
const browser=await chromium.launch({executablePath:homedir()+'/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell',args:['--use-angle=metal']});
try {
 const page=await browser.newPage({viewport:{width:390,height:850},isMobile:true,hasTouch:true,deviceScaleFactor:1});
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto(new URL('threejs-viewer.html',root).href);
 await page.waitForFunction(()=>window.runtimeReady||window.runtimeError);
 const error=await page.evaluate(()=>window.runtimeError);assert.equal(error,undefined);
 const probe=()=>page.evaluate(()=>window.runtimeProbe());
 const before=await probe(),bounds=await page.locator('canvas').boundingBox();
 assert.equal(before.viewMode,'default');assert.equal(before.viewportCount,2);assert.equal(before.orbitEnabled,true);
 const cdp=await page.context().newCDPSession(page);
 const touch=(type,points)=>cdp.send('Input.dispatchTouchEvent',{type,touchPoints:points.map(([x,y],id)=>({x,y,id}))});
 const x=bounds.x+bounds.width*.25,y=bounds.y+bounds.height*.5;
 await touch('touchStart',[[x,y]]);
 for(let i=1;i<=5;i++)await touch('touchMove',[[x+i*9,y+i*2]]);
 await touch('touchEnd',[]);
 const rotated=await probe();
 for(let i=0;i<2;i++)assert.ok(Math.hypot(...rotated.viewportCameras[i].position.map((v,j)=>v-before.viewportCameras[i].position[j]))>.02,'Touch must rotate both complementary cameras');
 assert.equal(rotated.playing,true);
 await page.waitForFunction(time=>window.runtimeProbe().animationTime!==time,rotated.animationTime);
 const cx=bounds.x+bounds.width*.5;
 await touch('touchStart',[[cx-35,y],[cx+35,y]]);
 for(let i=1;i<=4;i++)await touch('touchMove',[[cx-35-i*6,y],[cx+35+i*6,y]]);
 await touch('touchEnd',[]);
 const zoomed=await probe();
 assert.ok(Math.abs(zoomed.viewportCameras[0].zoom-rotated.viewportCameras[0].zoom)>.02,'Pinch must change zoom');
 assert.ok(Math.abs(zoomed.viewportCameras[0].zoom-zoomed.viewportCameras[1].zoom)<1e-8);
 await touch('touchStart',[[cx-35,y],[cx+35,y]]);
 for(let i=1;i<=3;i++)await touch('touchMove',[[cx-35+i*5,y+i*2],[cx+35+i*5,y+i*2]]);
 await touch('touchEnd',[]);
 const translated=await probe();
 assert.equal(translated.panEnabled,false);
 for(let i=0;i<2;i++)assert.ok(Math.hypot(...translated.viewportCameras[i].position.map((v,j)=>v-zoomed.viewportCameras[i].position[j]))<1e-8,'Two-finger translation must not pan the cameras');
 await page.locator('#reset-view').tap();
 const reset=await probe();
 for(let i=0;i<2;i++){
  const [px,py,pz]=presets['5965'][i].position,expected=[px,pz,-py];
  assert.ok(Math.hypot(...reset.viewportCameras[i].position.map((v,j)=>v-expected[j]))<1e-8);
  assert.equal(reset.viewportCameras[i].zoom,1);
 }
 assert.equal(reset.playing,true);assert.deepEqual(errors,[]);
 const report={ok:true,scope:'Chromium/Metal mobile touch emulation; not physical iOS/Android device evidence',viewport:{width:390,height:850},defaultRecommendedViews:2,singleFingerOrbitBothViews:true,pinchZoomBothViews:true,noPan:true,resetRecommendedCameras:true,animationContinues:true,errors};
 await writeFile(new URL('touch-verification.json',root),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
}finally{await browser.close();}
