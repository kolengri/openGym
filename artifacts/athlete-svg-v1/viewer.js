// Original anatomical vector study; motion samples come from our own rig.
const NS='http://www.w3.org/2000/svg',svg=document.querySelector('svg'),data=window.poseData;
const select=document.querySelector('#clip'),muscleInput=document.querySelector('#muscles'),scrub=document.querySelector('#time');
let clipName='Athlete_SquatPreview',time=0,playing=true,showMuscles=true;
const paths=new Map(),groups={};
function group(id,parent=svg){const g=document.createElementNS(NS,'g');g.id=id;parent.append(g);groups[id]=g;return g;}
function path(id,fill,parent,stroke='#91a5b5',width=.85){const p=document.createElementNS(NS,'path');p.id=id;for(const [k,v] of Object.entries({fill,stroke,'stroke-width':width,'stroke-linecap':'round','stroke-linejoin':'round'}))p.setAttribute(k,v);parent.append(p);paths.set(id,p);return p;}
const skin='#d3dfe8',armSkin='#e7eef4',farSkin='#b7c8d5',red='#e76859',amber='#e8b45b',neutral='#b8ccdb';
const ground=group('groundLayer');path('ground','#b8c5d0',ground,'none');
const defs=svg.querySelector('defs');
for(const side of ['Right','Left']){
 const g=group(side+'Leg');
 const clip=document.createElementNS(NS,'clipPath');clip.id=side+'LegClip';defs.append(clip);path(side+'legClipPath','#fff',clip,'none');
 path(side+'leg',skin,g,'#839aab',1.15);path(side+'foot',skin,g,'#839aab',1.15);
 const muscles=group(side+'LegAnatomy',g);muscles.setAttribute('clip-path',`url(#${side}LegClip)`);
 for(const id of ['quadOuter','quadMiddle','quadInner','hamstring','calfOuter','calfInner','soleus','tibialis'])path(side+id,neutral,muscles);
 for(const id of ['quadFibers','calfFibers','tendon','kneeCrease'])path(side+id,'none',g,'#8299ac',.65);
 path(side+'footDetails','none',g,'#8ba3b6',.65);
 path(side+'patella','#e6edf2',g,'#98aebe',.8);
}
function makeArm(side){const g=group(side+'Arm');path(side+'arm',armSkin,g,'#708b9f',1.5);
 const clip=document.createElementNS(NS,'clipPath');clip.id=side+'ArmClip';defs.append(clip);path(side+'armClipPath','#fff',clip,'none');
 const anatomy=group(side+'ArmAnatomy',g);anatomy.setAttribute('clip-path',`url(#${side}ArmClip)`);
 for(const id of ['deltoid','biceps','triceps','brachialis','forearmFlexor','forearmExtensor'])path(side+id,'#c6d5e1',anatomy,'#9aafbf',.65);
 path(side+'armFibers','none',g,'#91a7b8',.6);path(side+'armCreases','none',g,'#708b9f',.85);
 path(side+'hand',armSkin,g,'#708b9f',1.15);path(side+'fingers','none',g,'#91a7b8',.65);
}
makeArm('Right');
const body=group('body');path('pelvis',skin,body,'#839aab',1.1);path('torso',skin,body,'#839aab',1.1);
for(const id of ['pecLeft','pecRight','latLeft','latRight','obliqueLeft','obliqueRight','glute','hipFlexor','sideChest','sideBack','sideAbdominal'])path(id,neutral,body);
for(let i=0;i<8;i++)path('abs'+i,neutral,body);
for(const id of ['sternum','pecFibers','serratus','obliqueFibers','pelvisLines','sideFibers'])path(id,'none',body,'#94aaba',.7);
const head=group('headLayer');path('neck',skin,head,'#91a5b5',.9);path('neckLines','none',head,'#9eb2c1',.65);path('head',skin,head,'#839aab',1.1);path('headDetails','none',head,'#9bafbe',.7);
makeArm('Left');
const add=(a,b)=>[a[0]+b[0],a[1]+b[1]],sub=(a,b)=>[a[0]-b[0],a[1]-b[1]],mul=(a,t)=>[a[0]*t,a[1]*t],lerp=(a,b,t)=>add(mul(a,1-t),mul(b,t)),length=a=>Math.hypot(...a),unit=a=>mul(a,1/Math.max(.001,length(a)));
const fmt=a=>a.map(x=>Number(x.toFixed(2))).join(' ');
function closed(points){const n=points.length;let d='M'+fmt(points[0]);for(let i=0;i<n;i++){const p0=points[(i+n-1)%n],p1=points[i],p2=points[(i+1)%n],p3=points[(i+2)%n];d+=' C'+fmt(add(p1,mul(sub(p2,p0),1/6)))+' '+fmt(sub(p2,mul(sub(p3,p1),1/6)))+' '+fmt(p2);}return d+' Z';}
function basis(a,b){const u=unit(sub(b,a));return {u,n:[-u[1],u[0]]};}
function ribbon(a,b,coords){const {n}=basis(a,b);return closed(coords.map(([t,w])=>add(lerp(a,b,t),mul(n,w))));}
function ribbonLine(a,b,coords){const {n}=basis(a,b),p=coords.map(([t,w])=>add(lerp(a,b,t),mul(n,w)));return 'M'+fmt(p[0])+' Q'+fmt(p[1])+' '+fmt(p[2]);}
function limb(a,j,b,widths){const u=basis(a,j),v=basis(j,b),junction=unit(add(u.n,v.n));const samples=[{p:add(a,mul(u.u,-6)),n:u.n,w:widths[0]*.5},{p:a,n:u.n,w:widths[0]},{p:lerp(a,j,.34),n:u.n,w:widths[1]},{p:lerp(a,j,.77),n:u.n,w:widths[2]},{p:j,n:junction,w:widths[3]},{p:lerp(j,b,.34),n:v.n,w:widths[4]},{p:lerp(j,b,.72),n:v.n,w:widths[5]},{p:b,n:v.n,w:widths[6]}];return closed([...samples.map(q=>add(q.p,mul(q.n,q.w))),...samples.toReversed().map(q=>sub(q.p,mul(q.n,q.w)))]);}
function ellipse(c,rx,ry){return `M${c[0]-rx} ${c[1]} a${rx} ${ry} 0 1 0 ${2*rx} 0 a${rx} ${ry} 0 1 0 ${-2*rx} 0 Z`;}
function set(id,d,opacity=1){const p=paths.get(id);p.setAttribute('d',d);p.setAttribute('opacity',opacity);}
function muscle(id,d,activity=0,strength=1){set(id,d,activity&&showMuscles?strength:1);const p=paths.get(id);p.setAttribute('fill',activity&&showMuscles?(activity===2?amber:red):neutral);p.setAttribute('stroke',activity&&showMuscles?(activity===2?'#bd8c3d':'#b95249'):'#829caf');}
function clear(ids){for(const id of ids)set(id,'',0);}
function sample(t){const clip=data.clips[clipName],f=(t/clip.duration)*(clip.frames.length-1),i=Math.min(clip.frames.length-2,Math.floor(f)),u=f-i;return clip.frames[i].map((p,j)=>p.map((v,k)=>v*(1-u)+clip.frames[i+1][j][k]*u));}
function render(t){
 const clip=data.clips[clipName];time=Math.max(0,Math.min(t,clip.duration-1e-7));const frame=sample(time),world=Object.fromEntries(data.joints.map((n,i)=>[n,frame[i]])),squat=clipName.includes('Squat'),raise=clipName.includes('ArmRaise'),profile=squat;
 const scale=raise?248:282,project=p=>[profile?-p[1]:p[0],p[2]],xs=clip.frames.map(f=>project(f[0])[0]),center=(Math.min(...xs)+Math.max(...xs))/2;
 const point=p=>{const q=project(p);return[320+(q[0]-center)*scale,575-q[1]*scale];},p=Object.fromEntries(Object.entries(world).map(([n,v])=>[n,point(v)])),hips=p.Hips,neck=p.neck;
 set('ground',ellipse([hips[0],581],profile?103:114,12),.19);
 // True sagittal view for squats; frontal view for lateral movement and arm raises.
 if(profile)svg.insertBefore(groups.RightArm,body);else svg.append(groups.RightArm);svg.append(groups.LeftArm);
 for(const [side,sign] of [['Right',-1],['Left',1]]){
  const far=profile&&side==='Right',g=groups[side+'Leg'];g.setAttribute('opacity',far?.76:1);
  const hip=add(p[side+'UpLeg'],[0,-8]),knee=p[side+'Leg'],ankle=p[side+'Foot'],toe=p[side+'ToeBase'];
  const bend=Math.acos(Math.max(-1,Math.min(1,unit(sub(knee,hip)).reduce((s,v,i)=>s+v*unit(sub(ankle,knee))[i],0))))/Math.PI;
  const leg=limb(hip,knee,ankle,[22,24+3*bend,18,11,17,12,7]);set(side+'leg',leg);set(side+'legClipPath',leg);
  const foot=profile?closed([[ankle[0]-7,ankle[1]-3],[ankle[0]+7,ankle[1]+2],[ankle[0]+10,ankle[1]+16],[toe[0]+15,toe[1]+7],[toe[0]+20,toe[1]+12],[ankle[0]-10,toe[1]+15],[ankle[0]-13,toe[1]+9],[ankle[0]-11,ankle[1]+12]]):closed([[ankle[0]-7,ankle[1]-3],[ankle[0]+7,ankle[1]-3],[toe[0]+12,toe[1]+6],[toe[0]+14,toe[1]+13],[toe[0]-13,toe[1]+13],[toe[0]-14,toe[1]+6]]);set(side+'foot',foot);
  set(side+'footDetails',profile?`M${ankle[0]-6} ${ankle[1]+7} q8 2 8 10 M${toe[0]+9} ${toe[1]+10} q3 2 4 5`:`M${toe[0]-9} ${toe[1]+5} Q${toe[0]} ${toe[1]+1} ${toe[0]+9} ${toe[1]+5} M${ankle[0]} ${ankle[1]+5} L${toe[0]-2} ${toe[1]+1}`, .7);
  const load=raise?0:1,strength=squat?.72+.23*bend:.9;
  if(profile){
   muscle(side+'quadOuter',ribbon(hip,knee,[[.08,-7],[.20,-19],[.48,-19],[.79,-8],[.92,-3],[.78,1],[.32,4]]),load,strength);
   muscle(side+'quadMiddle',ribbon(hip,knee,[[.12,-2],[.25,-8],[.61,-7],[.86,-1],[.70,4],[.30,7]]),load,strength*.85);
   muscle(side+'quadInner',ribbon(hip,knee,[[.63,-8],[.78,-11],[.95,-2],[.90,3],[.75,3]]),load,strength);
   muscle(side+'hamstring',ribbon(hip,knee,[[.06,5],[.27,19],[.55,16],[.88,5],[.85,1],[.34,3]]),squat?1:0,squat?.54:1);
  }else{
   muscle(side+'quadOuter',ribbon(hip,knee,[[.07,-6],[.19,-18],[.51,-18],[.82,-9],[.91,-4],[.70,0],[.27,1]]),load,strength);
   muscle(side+'quadMiddle',ribbon(hip,knee,[[.09,1],[.24,-5],[.67,-4],[.84,1],[.67,7],[.26,8]]),load,strength*.9);
   muscle(side+'quadInner',ribbon(hip,knee,[[.27,11],[.49,17],[.76,14],[.94,3],[.85,0],[.64,6]]),load,strength);
   clear([side+'hamstring']);
  }
  muscle(side+'calfOuter',ribbon(knee,ankle,[[.12,profile?4:sign*3],[.26,profile?16:sign*11],[.53,profile?13:sign*10],[.77,profile?4:sign*4],[.55,profile?1:sign*2],[.26,profile?0:sign*2]]),raise?0:1,squat?.32:.82);
  muscle(side+'calfInner',ribbon(knee,ankle,[[.16,2],[.27,10],[.50,9],[.66,2],[.42,-1]]),profile?1:0,profile?.35:1);
  muscle(side+'soleus',ribbon(knee,ankle,[[.35,profile?14:sign*11],[.57,profile?11:sign*8],[.86,profile?2:sign*3],[.73,0],[.48,profile?5:sign*4]]),raise?0:1,squat?.30:.6);
  muscle(side+'tibialis',ribbon(knee,ankle,[[.13,-5],[.27,-11],[.57,-8],[.87,-2],[.82,1],[.41,-1]]));
  set(side+'quadFibers',[-11,-6,2,9].map(w=>ribbonLine(hip,knee,[[.20,w],[.47,w-2],[.76,w*.45]])).join(' '),.54);
  set(side+'calfFibers',[4,8,12].map(w=>ribbonLine(knee,ankle,[[.25,w],[.42,w-3],[.64,3]])).join(' '),.48);
  set(side+'tendon',ribbonLine(knee,ankle,[[.70,1],[.88,0],[1.02,0]])+' '+ribbonLine(hip,knee,[[.80,0],[.91,0],[1.04,0]]),.85);
  set(side+'patella',ribbon(hip,knee,[[.93,-5],[.99,-7],[1.05,-3],[1.07,3],[.99,7],[.94,4]]));
  set(side+'kneeCrease',ribbonLine(knee,ankle,[[.04,-7],[.07,0],[.04,7]]),.6);
 }
 const x=hips[0],y=hips[1],nx=neck[0],ny=neck[1];
 if(profile){
  const shoulder=lerp(p.LeftArm,p.RightArm,.5),hip=p.LeftUpLeg;
  set('torso',closed([[nx-14,ny-2],[nx+10,ny+1],[shoulder[0]+31,shoulder[1]+26],[x+27,y-23],[x+28,y+8],[x-28,y+13],[x-35,y-14],[shoulder[0]-29,shoulder[1]+30],[nx-20,ny+10]]));
  set('pelvis',closed([[x-28,y-10],[x+27,y-6],[hip[0]+21,hip[1]+15],[hip[0]-2,hip[1]+25],[x-35,y+30],[x-39,y+6]]));
  muscle('glute',closed([[x-24,y-7],[x-3,y+2],[hip[0]+7,hip[1]+13],[x-18,y+33],[x-35,y+24],[x-36,y+4]]),1,.78);
  muscle('hipFlexor',closed([[x+18,y-8],[x+26,y+6],[hip[0]+18,hip[1]+12],[hip[0]+8,hip[1]+11],[x+7,y+2]]));
  muscle('sideChest',closed([[shoulder[0]+2,shoulder[1]+8],[shoulder[0]+29,shoulder[1]+23],[shoulder[0]+23,shoulder[1]+43],[shoulder[0]-3,shoulder[1]+39],[shoulder[0]-10,shoulder[1]+21]]));
  muscle('sideBack',closed([[shoulder[0]-15,shoulder[1]+13],[shoulder[0]-6,shoulder[1]+46],[x-18,y-3],[x-28,y-7],[shoulder[0]-22,shoulder[1]+34]]));
  muscle('sideAbdominal',closed([[shoulder[0]+10,shoulder[1]+48],[shoulder[0]+21,shoulder[1]+45],[x+23,y-8],[x+6,y+4],[x-7,y-9]]),2,.82);
  for(let i=0;i<4;i++){const a=add(shoulder,[24,44]),b=add(hips,[24,-3]);muscle('abs'+i,ribbon(a,b,[[i*.23,0],[i*.23+.03,-4],[i*.23+.19,-4],[i*.23+.21,0],[i*.23+.18,4],[i*.23+.02,4]]),2,.9);}
  set('sideFibers',[0,1,2,3,4].map(i=>`M${nx+2+i*2} ${ny+73+i*8} q9 2 17 -7`).join(' '),.6);
  set('pelvisLines',`M${x+22} ${y+2} Q${hip[0]+3} ${hip[1]} ${hip[0]+2} ${hip[1]+15}`,.6);
  clear(['pecLeft','pecRight','latLeft','latRight','obliqueLeft','obliqueRight','sternum','pecFibers','serratus','obliqueFibers',...Array.from({length:4},(_,i)=>'abs'+(i+4))]);
 }else{
  const l=p.RightArm,r=p.LeftArm,cy=ny+42;
  set('torso',closed([[nx-17,ny-2],[l[0]+16,l[1]-8],[l[0]-8,l[1]+9],[l[0]+2,l[1]+39],[x-30,y-15],[x-29,y+10],[x+29,y+10],[x+30,y-15],[r[0]-2,r[1]+39],[r[0]+8,r[1]+9],[r[0]-16,r[1]-8],[nx+17,ny-2]]));
  set('pelvis',closed([[x-29,y-6],[x-38,y+8],[x-35,y+28],[x-18,y+37],[x,y+29],[x+18,y+37],[x+35,y+28],[x+38,y+8],[x+29,y-6]]));
  for(const [id,sign] of [['pecLeft',-1],['pecRight',1]])muscle(id,closed([[nx+sign*3,cy-18],[nx+sign*32,cy-21],[nx+sign*47,cy-10],[nx+sign*39,cy+8],[nx+sign*17,cy+13],[nx+sign*3,cy+7]]));
  for(const [id,sign] of [['latLeft',-1],['latRight',1]])muscle(id,closed([[nx+sign*44,cy+3],[nx+sign*38,cy+24],[x+sign*25,y-7],[x+sign*23,y-24],[nx+sign*28,cy+13]]));
  for(let i=0;i<8;i++){const row=Math.floor(i/2),sign=i%2?1:-1,top=cy+16+row*13,mid=lerp([nx,0],[x,0],.25+row*.18)[0]+sign*8.5;muscle('abs'+i,closed([[mid-6,top],[mid,top-1.6],[mid+6,top],[mid+6,top+8],[mid,top+10],[mid-6,top+8]]),2,.82);}
  for(const [id,sign] of [['obliqueLeft',-1],['obliqueRight',1]])muscle(id,closed([[nx+sign*25,cy+16],[nx+sign*33,cy+22],[x+sign*25,y+2],[x+sign*15,y+6],[x+sign*17,y-18]]),2,.65);
  set('sternum',`M${nx} ${cy-21} Q${nx+1} ${cy-3} ${nx} ${cy+11}`,.7);
  set('pecFibers',[-1,1].flatMap(sign=>[0,1,2,3].map(i=>`M${nx+sign*5} ${cy-9+i*5} Q${nx+sign*22} ${cy-9+i*5} ${nx+sign*(39-i*2)} ${cy-13+i*6}`)).join(' '),.5);
  set('serratus',[-1,1].flatMap(sign=>[0,1,2].map(i=>`M${nx+sign*(38-i*3)} ${cy+14+i*7} l${sign*-9} 6`)).join(' '),.7);
  set('obliqueFibers',[-1,1].flatMap(sign=>[0,1,2].map(i=>`M${x+sign*29} ${y-20+i*7} l${sign*-10} 8`)).join(' '),.65);
  set('pelvisLines',`M${x-28} ${y+2} Q${x-18} ${y+8} ${x-10} ${y+20} M${x+28} ${y+2} Q${x+18} ${y+8} ${x+10} ${y+20}`,.55);
  clear(['glute','hipFlexor','sideChest','sideBack','sideAbdominal','sideFibers']);
 }
 const headBase=p.Head,hc=lerp(p.Head,p.head_end,.49),hx=hc[0],hy=hc[1];
 set('neck',closed([[headBase[0]-13,headBase[1]-5],[headBase[0]+12,headBase[1]-5],[nx+16,ny+9],[nx-16,ny+9]]));
 set('neckLines',`M${headBase[0]-7} ${headBase[1]+2} Q${nx-6} ${ny+1} ${nx-12} ${ny+9} M${headBase[0]+7} ${headBase[1]+2} Q${nx+6} ${ny+1} ${nx+12} ${ny+9}`,.65);
 if(profile){
  set('head',closed([[hx-13,hy+23],[hx-22,hy+2],[hx-23,hy-19],[hx-12,hy-31],[hx+9,hy-31],[hx+19,hy-20],[hx+19,hy-8],[hx+27,hy+3],[hx+24,hy+9],[hx+17,hy+10],[hx+13,hy+28],[hx+3,hy+32]]));
  set('headDetails',`M${hx-6} ${hy-3} c-7 -6 -9 5 -3 10 M${hx+10} ${hy+19} q-4 5 -10 6`,.65);
 }else{
  set('head',closed([[hx-19,hy-17],[hx-19,hy-28],[hx-8,hy-35],[hx+8,hy-35],[hx+20,hy-26],[hx+21,hy-12],[hx+18,hy+12],[hx+9,hy+29],[hx,hy+33],[hx-11,hy+28],[hx-19,hy+10]]));
  set('headDetails',`M${hx-17} ${hy+9} Q${hx} ${hy+24} ${hx+17} ${hy+9} M${hx} ${hy-8} l-2 15 5 1`,.3);
 }
 for(const side of ['Right','Left']){
  const far=profile&&side==='Right',shoulder=p[side+'Arm'],elbow=p[side+'ForeArm'],wrist=p[side+'Hand'];groups[side+'Arm'].setAttribute('opacity',far?.8:1);
  paths.get(side+'arm').setAttribute('fill',far?farSkin:armSkin);paths.get(side+'hand').setAttribute('fill',far?farSkin:armSkin);
  const arm=limb(shoulder,elbow,wrist,[18,16,12,8,12,8,5.5]);set(side+'arm',arm);set(side+'armClipPath',arm);
  muscle(side+'deltoid',ribbon(shoulder,elbow,[[-.08,-4],[.02,-15],[.19,-16],[.38,-6],[.45,0],[.31,8],[.10,16],[-.05,11]]),raise?1:0,.9);
  paths.get(side+'deltoid').setAttribute('transform',raise?`translate(${side==='Left'?8:-8} -7)`:'');
  muscle(side+'biceps',ribbon(shoulder,elbow,[[.29,-1],[.43,-10],[.65,-11],[.83,-4],[.88,1],[.67,6],[.43,7]]));
  muscle(side+'triceps',ribbon(shoulder,elbow,[[.23,10],[.43,15],[.71,10],[.93,3],[.77,0],[.46,5]]));
  muscle(side+'brachialis',ribbon(shoulder,elbow,[[.55,-12],[.74,-12],[.92,-4],[.90,-1],[.72,-6]]));
  muscle(side+'forearmFlexor',ribbon(elbow,wrist,[[.10,-3],[.22,-10],[.49,-9],[.82,-2],[.89,0],[.54,3],[.23,5]]));
  muscle(side+'forearmExtensor',ribbon(elbow,wrist,[[.10,4],[.24,10],[.54,8],[.90,2],[.72,0],[.42,3]]));
  set(side+'armFibers',[-5,0,5].map(w=>ribbonLine(shoulder,elbow,[[.40,w],[.61,w-1],[.82,w*.3]])).join(' ')+' '+[-4,0,4].map(w=>ribbonLine(elbow,wrist,[[.22,w],[.57,w*.5],[.92,0]])).join(' '),.65);
  set(side+'armCreases',ribbonLine(elbow,wrist,[[.01,-6],[.06,0],[.01,6]])+' '+ribbonLine(elbow,wrist,[[.96,-5],[.99,0],[.96,5]]),.85);
  const {u,n}=basis(elbow,wrist),h=q=>add(wrist,add(mul(u,q[0]),mul(n,q[1])));
  set(side+'hand',closed([[0,-5],[7,-8],[16,-7],[21,-3],[20,5],[14,8],[7,8],[3,4],[-1,4]].map(h)));
  set(side+'fingers',[7,11,15].map(a=>'M'+fmt(h([a,-6]))+' L'+fmt(h([a,3]))).join(' '),.65);
 }
 scrub.max=clip.duration;scrub.value=time;document.querySelector('#clock').textContent=`${time.toFixed(1)} / ${clip.duration.toFixed(1)} с`;
 document.querySelector('#view-label').textContent=profile?'Сбоку · движение в плоскости кадра':'Спереди · движение в плоскости кадра';
 document.querySelector('#zones').textContent=raise?'Дельтовидные · пресс стабилизирует корпус':squat?'Квадрицепсы и ягодичные · пресс стабилизирует корпус':'Квадрицепсы и икроножные · пресс стабилизирует корпус';
}
select.onchange=()=>{clipName=select.value;time=0;render(0);};muscleInput.onchange=()=>{showMuscles=muscleInput.checked;render(time);};document.querySelector('#play').onclick=()=>{playing=!playing;document.querySelector('#play').textContent=playing?'Пауза':'Пуск';};scrub.oninput=()=>{playing=false;document.querySelector('#play').textContent='Пуск';render(Number(scrub.value));};
window.svgDemo={render:t=>{playing=false;render(t);},select:name=>{clipName=name;select.value=name;render(0);},setMuscles:v=>{showMuscles=v;muscleInput.checked=v;render(time);},paths:()=>Object.fromEntries([...paths].map(([id,p])=>[id,{d:p.getAttribute('d'),opacity:p.getAttribute('opacity')}]))};
select.value=clipName;render(1.4);let last=performance.now();function tick(now){const dt=Math.min(.1,(now-last)/1000);last=now;if(playing)render((time+dt)%data.clips[clipName].duration);requestAnimationFrame(tick);}requestAnimationFrame(tick);
