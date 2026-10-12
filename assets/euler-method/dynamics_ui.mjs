import {MAX_TIME} from './time-range.mjs';
/** General ODE systems and Cucker–Smale: isolated UI, leaves scalar ODE intact. */
import {panByPixels, dragRotates, arrowMovement} from './camera.mjs';
import {compileLatex} from './latex.mjs';
import {PixelPainter} from './pixel.mjs';
import {
  systemAtTime, parseInitialStates, systemRhs,
  cuckerInitial, cuckerStep, cuckerDiagnostics,
} from './dynamics_math.mjs';

const root=document.getElementById('euler-lab');
if(!root)throw new Error('ODE Lab root is absent.');
const el=id=>root.querySelector(`#${id}`);
const canvas=el('dl-canvas'),ctx=canvas.getContext('2d');
const pixel=document.createElement('canvas'),pg=pixel.getContext('2d');
const palette=['#e84349','#007bcb','#02986f','#aa56c9','#d48d24','#4864a2','#b45b4c','#009da8','#7773b5','#8b773a'];
const clamp=(x,min,max)=>Math.max(min,Math.min(max,x));
const finite=x=>Number.isFinite(x);
const format=x=>finite(x)?(Math.abs(x)>9999||Math.abs(x)<.0001&&x!==0?x.toExponential(2):x.toFixed(3).replace(/\.?0+$/,'')):'—';
const setText=(id,text)=>{el(id).textContent=text;};
const mode=root.dataset.mode;
if(!['system','cucker'].includes(mode))throw new Error('Unknown dynamics page.');
let dimension=2,method='rk4',plotMode='phase',time=0,playing=false,lastTick=null, speed=1;
let scale=48,pan=[0,0],yaw=.48,pitch=.4;
let width=760,height=510,dpr=1,drag=null,dirty=true,valid=false;
let systemFn=null,paths=[],maxT=MAX_TIME,step=.02;
let csInitial=null,csFrame=null,csFrames=[],csTrails=[],csMetrics=[],csTime=0,csTarget=0,csStep=.02,csN=80,csConfig=null,csError='';
let csOriginalStart=false,csTick=0,csStride=1;
let renderRequested=false;

const systemInputs=['dl-dx','dl-dy','dl-dz','dl-initial','dl-dim','dl-step','dl-tmax','dl-method'];
const currentExpressions=()=>[el('dl-dx').value,el('dl-dy').value,...(dimension===3?[el('dl-dz').value]:[])];
function setError(text){setText('dl-system-error',text);el('dl-system-error').hidden=!text;}
function resize(){
  if(mode==='scalar')return;
  const rect=canvas.getBoundingClientRect();
  if(rect.width<40)return;
  width=rect.width;height=rect.height;dpr=Math.min(window.devicePixelRatio||1,2);
  canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);
  ctx.setTransform(dpr,0,0,dpr,0,0);
  pixel.width=Math.ceil(width);pixel.height=Math.ceil(height);
  pg.setTransform(1,0,0,1,0,0);
  queue();
}
const painter=()=>new PixelPainter(pg,width,height,1);
const worldToScreen=(x,y)=>[width/2+(x-pan[0])*scale,height/2-(y-pan[1])*scale];
function projection(values){
  const [x,y,z=0]=values;
  const c=Math.cos(yaw),s=Math.sin(yaw),p=Math.cos(pitch),q=Math.sin(pitch);
  return [c*x+s*z,p*y+q*(s*x-c*z)];
}
const project=values=>{
  const [x,y]=projection(values);
  return worldToScreen(x,y);
};
function worldFromScreen(px,py){return [(px-width/2)/scale+pan[0],(height/2-py)/scale+pan[1]];}
function grid(){
  ctx.fillStyle='#fbfdff';ctx.fillRect(0,0,width,height);
  const [left,bottom]=worldFromScreen(0,height),[right,top]=worldFromScreen(width,0);
  const raw=75/scale,pow=10**Math.floor(Math.log10(raw)),unit=([1,2,5,10].find(n=>n*pow>=raw)||10)*pow;
  ctx.lineWidth=1;ctx.strokeStyle='#e6edf6';ctx.beginPath();
  for(let x=Math.ceil(left/unit)*unit;x<right;x+=unit){const sx=worldToScreen(x,0)[0];ctx.moveTo(sx,0);ctx.lineTo(sx,height);}
  for(let y=Math.ceil(bottom/unit)*unit;y<top;y+=unit){const sy=worldToScreen(0,y)[1];ctx.moveTo(0,sy);ctx.lineTo(width,sy);}
  ctx.stroke();ctx.strokeStyle='#95a9c1';ctx.beginPath();
  const [ax,ay]=worldToScreen(0,0);
  if(ax>=0&&ax<=width){ctx.moveTo(ax,0);ctx.lineTo(ax,height);}
  if(ay>=0&&ay<=height){ctx.moveTo(0,ay);ctx.lineTo(width,ay);}
  ctx.stroke();
}
function line(p,a,b,color){p.line(a[0],a[1],b[0],b[1],color);}
function pathPixel(p,points,color){
  for(let i=1;i<points.length;i++){
    const a=points[i-1],b=points[i];
    if(a.every(finite)&&b.every(finite))line(p,a,b,color);
  }
}
function marker(px,py,color,size=4){
  if(!finite(px)||!finite(py)||px < -10 ||py < -10 ||px>width+10 ||py>height+10)return;
  ctx.beginPath();ctx.arc(px,py,size,0,2*Math.PI);
  ctx.fillStyle='#fff';ctx.fill();ctx.strokeStyle=color;ctx.lineWidth=1;ctx.stroke();
}
function plotXY(t,values,dimensionArg=dimension){
  if(plotMode==='series')return worldToScreen(t,values[0]);
  return dimensionArg===3?project(values):worldToScreen(values[0],values[1]);
}
/** Center and scale the current mathematical data without changing the solution. */
function fitView(){
  let samples=[];
  if(mode==='system' && paths.length){
    for(const path of paths){
      const stride=Math.max(1,Math.floor(path.points.length/1300));
      for(let i=0;i<path.points.length;i+=stride){
        const point=path.points[i];
        if(plotMode==='series'){
          for(let comp=0;comp<dimension;comp++)samples.push([point.t,point.values[comp]]);
        }else samples.push(dimension===3?projection(point.values):point.values.slice(0,2));
      }
    }
  } else if(mode==='cucker'&&csFrame){
    if(el('dl-c-plot').value==='alignment')samples=[[0,0],[Math.max(csTime,1),Math.max(0.5,...csMetrics)*1.10],...csMetrics.map((v,i)=>[i*csStride*csStep,v])];
    else for(const point of cuckerSamples(csFrame))samples.push(projection(point));
  }
  samples=samples.filter(p=>p.length===2&&p.every(Number.isFinite));
  if(!samples.length){pan=[0,0];scale=mode==='cucker'?25:48;queue();return;}
  const lo=[Infinity,Infinity],hi=[-Infinity,-Infinity];
  for(const p of samples)for(let k=0;k<2;k++){
    lo[k]=Math.min(lo[k],p[k]);hi[k]=Math.max(hi[k],p[k]);
  }
  pan=[(lo[0]+hi[0])/2,(lo[1]+hi[1])/2];
  const spanX=Math.max(hi[0]-lo[0],.5),spanY=Math.max(hi[1]-lo[1],.5);
  scale=clamp(Math.min((width-90)/spanX,(height-90)/spanY),5,200);
  queue();
}
function renderVectorField(p){
  if(dimension!==2 || plotMode!=='phase' ||!systemFn||!el('dl-field').checked)return;
  for(let sy=18;sy<height;sy+=40)for(let sx=18;sx<width;sx+=40){
    const state=worldFromScreen(sx,sy);let vector;
    try{vector=systemFn(0,state);}catch{continue;}
    const norm=Math.hypot(vector[0],vector[1]);if(!(norm>1e-12)&&norm!==0)continue;
    if(!finite(norm))continue;
    const ux=norm>1e-12?vector[0]/norm:0,uy=norm>1e-12?-vector[1]/norm:0;
    const a=[sx-ux*9,sy-uy*9],b=[sx+ux*9,sy+uy*9];
    line(p,a,b,'#2954ed');
    const head=4,side=2;
    line(p,b,[b[0]-ux*head-uy*side,b[1]-uy*head+ux*side],'#2954ed');
    line(p,b,[b[0]-ux*head+uy*side,b[1]-uy*head-ux*side],'#2954ed');
  }
}
function drawAxes3d(p){
  const origin=project([0,0,0]);
  for(let axis=0;axis<3;axis++){
    const endpoint=[0,0,0];endpoint[axis]=6;
    const projected=project(endpoint);
    line(p,origin,projected,['#de5b65','#2b9e75','#3a63da'][axis]);
    ctx.fillStyle=['#b84a56','#158362','#3159bc'][axis];
    ctx.font='12px ui-monospace,monospace';ctx.fillText(['x','y','z'][axis],projected[0]+5,projected[1]-3);
  }
}
function pointSeries(path,index){return path.points.map(q=>worldToScreen(q.t,q.values[index]));}
function renderSystem(p){
  if(!valid ||!paths.length)return;
  if(plotMode==='phase' && dimension===3)drawAxes3d(p);
  else if(plotMode==='phase')renderVectorField(p);
  paths.forEach((path,idx)=>{
    const color=palette[idx%palette.length];
    if(plotMode==='series'){
      for(let comp=0;comp<dimension;comp++)pathPixel(p,pointSeries(path,comp),comp===0?color:palette[(idx+comp+2)%palette.length]);
      const at=systemAtTime(path.points,time);
      if(at)for(let comp=0;comp<dimension;comp++){
        const [x,y]=worldToScreen(time,at[comp]);marker(x,y,comp===0?color:palette[(idx+comp+2)%palette.length],3);
      }
    }else{
      pathPixel(p,path.points.map(q=>plotXY(q.t,q.values)),color);
      const at=systemAtTime(path.points,time);
      if(at){const [x,y]=plotXY(time,at);marker(x,y,color,5);}
    }
  });
  if(plotMode==='series'){
    ctx.font='11px ui-monospace,monospace';ctx.fillStyle='#70839d';ctx.fillText('t →',Math.max(8,width-38),height-12);
  }
}
function cuckerSamples(frame){
  const n=csN;
  const points=[];
  for(let i=0;i<n;i++)points.push([frame.positions[3*i],frame.positions[3*i+1],frame.positions[3*i+2]]);
  return points;
}
function renderCucker(p){
  if(!csFrame)return;
  const n=csN;
  if(el('dl-c-plot').value==='alignment'){
    const pts=csMetrics.map((v,i)=>worldToScreen(i*csStride*csStep,v));
    pathPixel(p,pts,'#2054a4');
    const val=cuckerDiagnostics(csFrame,csN).dispersion;
    const point=worldToScreen(csTime,val);
    marker(point[0],point[1],'#e84349',5);
    ctx.fillStyle='#73859a';ctx.font='11px ui-monospace,monospace';ctx.fillText('σ(t)',9,15);
  }else{
  drawAxes3d(p);
  const pos=csFrame.positions;
  // A small number of traced particles and a bounded trail history keep N=250 responsive.
  if(el('dl-trails').checked && csTrails.length>=2){
    for(let i=0;i<Math.min(csN,32);i++){
      const series=csTrails.map(f=>project([f.positions[3*i],f.positions[3*i+1],f.positions[3*i+2]]));
      pathPixel(p,series,'#9db0c8');
    }
  }
  for(let i=0;i<n;i++){
    const [x,y]=project([pos[3*i],pos[3*i+1],pos[3*i+2]]);
    p.point(x,y,palette[i%palette.length],2);
  }
  }
  const stat=cuckerDiagnostics(csFrame,n);
  setText('dl-metrics',`t = ${format(csTime)}  ·  N = ${n}\nvelocity σ = ${format(stat.dispersion)}\nmax |vᵢ−vⱼ| = ${format(stat.maxGap)}\nmean v = (${stat.mean.map(format).join(', ')})`);
}
function stepRuler(){
  const min=.001,max=mode==='system'?1:.1;
  const current=mode==='system'?step:csStep;
  const left=20,right=Math.min(width-25,224),y=height-32;
  const fraction=clamp(Math.log(clamp(current,min,max)/min)/Math.log(max/min),0,1);
  return {left,right,y,handle:left+(right-left)*fraction,min,max};
}
function isOnRuler(x,y){
  if(mode==='system'&&!valid)return false;
  const r=stepRuler();return x>=r.left-9&&x<=r.right+9&&Math.abs(y-r.y)<=21;
}
function applyRuler(x){
  const r=stepRuler();
  const fraction=clamp((x-r.left)/(r.right-r.left),0,1);
  const h=Number((r.min*Math.pow(r.max/r.min,fraction)).toPrecision(5));
  if(mode==='system'){
    el('dl-step').value=String(h);
    el('dl-step-range').value=String(Math.round(clamp(Math.log(h/.001)/Math.log(1000),0,1)*1000));
    makeVectorField({fit:false});
  }else{
    el('dl-cstep').value=String(h);cuckerReset();
  }
}
function renderRuler(){
  if(mode==='system'&&!valid)return;
  const r=stepRuler();
  ctx.save();
  ctx.fillStyle='rgba(255,255,255,.94)';ctx.fillRect(r.left-10,r.y-27,r.right-r.left+25,46);
  ctx.font='11px ui-monospace,Menlo,monospace';ctx.fillStyle='#335a83';
  ctx.fillText(`drag h  ${format(mode==='system'?step:csStep)}`,r.left,r.y-9);
  ctx.lineWidth=1;ctx.strokeStyle='#b0c5dc';ctx.beginPath();ctx.moveTo(r.left,r.y+5);ctx.lineTo(r.right,r.y+5);ctx.stroke();
  ctx.beginPath();ctx.arc(r.handle,r.y+5,5,0,2*Math.PI);ctx.fillStyle='#2054a4';ctx.fill();
  ctx.restore();
}
function draw(){
  renderRequested=false;
  if(mode==='scalar')return;
  grid();pg.clearRect(0,0,width,height);
  const p=painter();
  if(mode==='system')renderSystem(p);else renderCucker(p);
  ctx.save();ctx.imageSmoothingEnabled=false;ctx.drawImage(pixel,0,0,width,height);ctx.restore();
  renderRuler();
  setText('dl-coordinates',mode==='system'?`${dimension}D · ${plotMode==='phase'?'phase space':'time series'}`:`3D · ${csN} agents`);
}
function queue(){if(renderRequested)return;renderRequested=true;requestAnimationFrame(draw);}
function syncTime(){
  const s=el('dl-time');
  const max=mode==='system'?maxT:MAX_TIME;
  s.max=String(max);s.value=String(clamp(time,0,max));
  setText('dl-time-value',`t = ${format(time)}`);
  setText('dl-play',playing?'Ⅱ Pause':'▶ Play');
  el('dl-play').disabled=mode==='system'?!valid:!csFrame;
}
function seek(value){
  time=clamp(Number(value)||0,0,mode==='system'?maxT:MAX_TIME);
  if(mode==='cucker')csTarget=time;
  syncTime();queue();
}
let systemWorker=null;
function makeVectorField({fit=true}={}){
  systemWorker?.terminate();
  const expr=currentExpressions();
  if(expr.some(x=>!x.trim())){systemFn=null;paths=[];valid=false;setError('');setText('dl-result','');syncTime();queue();return;}
  try{
    const fs=expr.map((s,i)=>compileLatex(systemRhs(s,['x','y','z'][i]),['t','x','y','z']));
    const initial=parseInitialStates(el('dl-initial').value,dimension);
    step=Number(el('dl-step').value);maxT=Number(el('dl-tmax').value);
    if(!(step>=0.001 && step<=1 && finite(step)))throw new RangeError('Step size must be in [0.001, 1].');
    if(!(maxT>=0.1 && maxT<=MAX_TIME && finite(maxT)))throw new RangeError('Time span must be in [0.1, 1000].');
    method=el('dl-method').value;plotMode=el('dl-plot').value;
    systemFn=(t,v)=>fs.map(f=>f(t,v[0],v[1],v[2]??0));
    paths=[];valid=false;playing=false;syncTime();queue();setText('dl-result','Computing…');
    systemWorker=new Worker(new URL('./solver-worker.mjs',import.meta.url),{type:'module'});
    systemWorker.onmessage=({data})=>{
    if(data.error){setError(data.error);return;}
    const results=data.results;paths=results;valid=true;
    const errors=results.filter(r=>r.stopped).map(r=>r.reason);
    setError(errors[0]||'');
    setText('dl-result',`${method.toUpperCase()} · ${results.length} initial state${results.length===1?'':'s'} · ${results.map(p=>Math.round(p.points.at(-1).t/step)).join('/')} steps`);
    el('dl-time').max=String(maxT);time=clamp(time,0,maxT);
    syncTime();if(fit)fitView();queue();
    };
    systemWorker.onerror=()=>setError('Unable to compute numerical solution.');
    systemWorker.postMessage({kind:'system',expressions:expr,initial,tMax:maxT,h:step,method});
  }catch(error){valid=false;paths=[];systemFn=null;playing=false;setError(error.message);setText('dl-result','');syncTime();queue();}
}
function setDimensions(n){dimension=n;el('dl-z-wrap').hidden=n!==3;el('dl-field').disabled=n===3;el('dl-plot').value='phase';plotMode='phase';scale=n===3?40:48;pan=[0,0];makeVectorField();}
function clearSystem(){
  for(const id of ['dl-dx','dl-dy','dl-dz','dl-initial'])el(id).value='';
  el('dl-preset').value='';playing=false;time=0;makeVectorField();
}
function applyPreset(name){
  const presets={
    oscillator:{n:2,eq:['y','-x'],init:'1, 0; 0, 1',time:25},
    vdp:{n:2,eq:['y',String.raw`(1-x^2)y-x`],init:'2, 0; 0.5, 0',time:30},
    predator:{n:2,eq:['x(1-y)','y(x-1)'],init:'1.3, 1; 0.8, 1.2',time:30},
    lorenz:{n:3,eq:['10(y-x)','x(28-z)-y',String.raw`xy-\frac{8}{3}z`],init:'1, 1, 1; 1.01, 1, 1',time:25},
    rossler:{n:3,eq:['-y-z','x+0.2y','0.2+z(x-5.7)'],init:'0, 1, 0; 0.01, 1, 0',time:35},
  };
  if(!name){clearSystem();return;}
  const preset=presets[name];if(!preset)return;
  dimension=preset.n;el('dl-dim').value=String(dimension);
  for(let i=0;i<3;i++)el(['dl-dx','dl-dy','dl-dz'][i]).value=preset.eq[i]||'';
  el('dl-initial').value=preset.init;el('dl-tmax').value=String(MAX_TIME);
  el('dl-step').value=preset.n===3?'0.01':'0.02';
  time=0;playing=false;setDimensions(dimension);syncTime();
}
function cuckerReset(){
  const n=Number(el('dl-n').value),h=Number(el('dl-cstep').value),lambda=Number(el('dl-lambda').value);
  const beta=Number(el('dl-beta').value),seed=Number(el('dl-seed').value);
  const spread=Number(el('dl-spread').value),vspread=Number(el('dl-vspread').value);
  if(!Number.isInteger(n)||n<2||n>250||!(h>=.001&&h<=.1)||!(lambda>=0&&lambda<=100)||!(beta>=0&&beta<=5)||!Number.isInteger(seed)||!(spread>=0&&spread<=50)||!(vspread>=0&&vspread<=100)){
    setText('dl-result','Check N (2–250), λ (0–100), h (0.001–0.1), β (0–5), seed, and spreads.');return;
  }
  playing=false;time=0;csTarget=0;csTime=0;csN=n;csStep=h;
  csConfig={h,lambda,kernel:el('dl-kernel').value,beta,method:el('dl-cmethod').value};
  csInitial=cuckerInitial(n,seed,spread,vspread);
  if(csOriginalStart)csInitial.positions.fill(10);
  csTick=0;csStride=Math.max(1,Math.ceil(MAX_TIME/h/1000));
  csFrame=csInitial;csFrames=[csInitial];csTrails=[csInitial];csError='';csMetrics=[cuckerDiagnostics(csInitial,n).dispersion];
  scale=25;pan=[0,0];yaw=.6;pitch=.38;
  setText('dl-result',`N = ${n} · ${csConfig.method.toUpperCase()} · h = ${format(h)}`);
  syncTime();fitView();queue();
}
function updateCucker(target,limit=200){
  if(!csFrame)return;
  const tick=Math.round(target/csStep);
  if(tick<csTick){
    const checkpoint=Math.min(Math.floor(tick/csStride),csFrames.length-1);
    csTick=checkpoint*csStride;csFrame=csFrames[checkpoint];csTrails=[];
  }
  const deadline=performance.now()+12;
  try{
    for(let i=0;i<limit && csTick<tick && performance.now()<deadline;i++){
      csFrame=cuckerStep(csFrame,csN,csConfig);csTick++;
      if(csTick%csStride===0){
        csFrames[csTick/csStride]=csFrame;
        csMetrics[csTick/csStride]=cuckerDiagnostics(csFrame,csN).dispersion;
      }
      if(csTick%3===0)csTrails.push(csFrame);
      if(csTrails.length>240)csTrails.shift();
    }
    csTime=csTick*csStep;
  }catch(e){playing=false;csError=e.message;setText('dl-result',csError);}
}
if(mode==='system'){
let editTimer;
for(const id of systemInputs){
  if(id==='dl-dim')continue;
  el(id).addEventListener('input',()=>{
    if(id==='dl-step')el('dl-step-range').value=String(Math.round(clamp(Math.log(Number(el('dl-step').value)/.001)/Math.log(1000),0,1)*1000));
    clearTimeout(editTimer);editTimer=setTimeout(makeVectorField,180);
  });
}
el('dl-dim').addEventListener('change',()=>setDimensions(Number(el('dl-dim').value)));
el('dl-step-range').addEventListener('input',()=>{
  el('dl-step').value=Number((.001*Math.pow(1000,Number(el('dl-step-range').value)/1000)).toPrecision(5));makeVectorField();
});
el('dl-plot').addEventListener('change',()=>{plotMode=el('dl-plot').value;fitView();queue();});
el('dl-field').addEventListener('change',queue);
el('dl-preset').addEventListener('change',()=>applyPreset(el('dl-preset').value));
el('dl-clear-system').addEventListener('click',clearSystem);
}
if(mode==='cucker'){
el('dl-c-reset').addEventListener('click',cuckerReset);
el('dl-c-original').addEventListener('click',()=>{csOriginalStart=true;el('dl-n').value='250';el('dl-lambda').value='100';el('dl-cstep').value='0.01';el('dl-kernel').value='original';el('dl-seed').value='23';el('dl-spread').value='0';el('dl-vspread').value='100';cuckerReset();});
for(const id of ['dl-n','dl-lambda','dl-beta','dl-seed','dl-kernel','dl-cstep','dl-cmethod','dl-spread','dl-vspread'])el(id).addEventListener('change',()=>{csOriginalStart=false;cuckerReset();});
el('dl-c-plot').addEventListener('change',()=>{fitView();queue();});
el('dl-trails').addEventListener('change',queue);
}
el('dl-fit').addEventListener('click',fitView);
el('dl-export').addEventListener('click',()=>{
  const lines=[];
  if(mode==='system'){
    if(!valid||!paths.length)return;
    lines.push(['initial_index','t','x','y',...(dimension===3?['z']:[])].join(','));
    paths.forEach((path,idx)=>{
      for(const point of path.points)lines.push([idx+1,point.t,...point.values].join(','));
    });
  }else{
    lines.push('t,velocity_dispersion');
    for(let i=0;i<csMetrics.length;i++)lines.push([i*csStride*csStep,csMetrics[i]].join(','));
  }
  const url=URL.createObjectURL(new Blob([lines.join('\n')+'\n'],{type:'text/csv;charset=utf-8'}));
  const a=document.createElement('a');a.href=url;a.download=mode==='system'?'ode-system-trajectories.csv':'cucker-smale-alignment.csv';
  document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),3000);
});
el('dl-play').addEventListener('click',()=>{if(mode==='system'&&!valid)return;playing=!playing;lastTick=null;syncTime();if(playing)requestAnimationFrame(frame);});
el('dl-reset-time').addEventListener('click',()=>{playing=false;seek(0);});
el('dl-time').addEventListener('pointerdown',()=>{playing=false;syncTime();});
el('dl-time').addEventListener('input',()=>{const requested=Number(el('dl-time').value);playing=false;seek(requested);requestAnimationFrame(frame);});
el('dl-speed').addEventListener('change',()=>{speed=Number(el('dl-speed').value);});
canvas.addEventListener('pointerdown',e=>{
  if(e.button!==0&&e.pointerType==='mouse')return;
  canvas.focus({preventScroll:true});
  if(isOnRuler(e.offsetX,e.offsetY)){drag={mode:'step'};canvas.setPointerCapture(e.pointerId);applyRuler(e.offsetX);return;}
  drag={x:e.offsetX,y:e.offsetY,pan:pan.slice(),yaw,pitch};
  canvas.setPointerCapture(e.pointerId);canvas.classList.add('is-moving');
});
canvas.addEventListener('pointermove',e=>{
  const coordinates=worldFromScreen(e.offsetX,e.offsetY);
  setText('dl-coordinates',`x ${format(coordinates[0])} · y ${format(coordinates[1])}`);
  if(!drag)return;
  if(drag.mode==='step'){applyRuler(e.offsetX);return;}
  const dx=e.offsetX-drag.x,dy=e.offsetY-drag.y;
  const in3d=mode==='cucker'?el('dl-c-plot').value==='agents':dimension===3&&plotMode==='phase';
  if(dragRotates(mode,in3d,e.shiftKey)){yaw=drag.yaw+dx*.007;pitch=clamp(drag.pitch+dy*.007,-1.5,1.5);}
  else pan=panByPixels(drag.pan,dx,dy,scale);
  queue();
});
for(const evt of ['pointerup','pointercancel'])canvas.addEventListener(evt,()=>{drag=null;canvas.classList.remove('is-moving');});
canvas.addEventListener('keydown',e=>{
  if(mode!=='cucker'||e.ctrlKey||e.metaKey||e.altKey)return;
  const delta=arrowMovement(e.key);if(!delta)return;
  e.preventDefault();pan=panByPixels(pan,...delta,scale);queue();
});
canvas.addEventListener('wheel',e=>{
  e.preventDefault();const old=worldFromScreen(e.offsetX,e.offsetY);
  scale=clamp(scale*Math.exp(-e.deltaY*.003),5,250);
  const after=worldFromScreen(e.offsetX,e.offsetY);
  pan[0]+=old[0]-after[0];pan[1]+=old[1]-after[1];queue();
},{passive:false});
function frame(now){
  if(mode==='scalar')return;
  const elapsed=lastTick===null?0:clamp((now-lastTick)/1000,0,.08);lastTick=now;
  if(playing){
    const max=mode==='system'?maxT:MAX_TIME;
    time=clamp(time+elapsed*speed,0,max);
    if(time>=max)playing=false;
  }
  if(mode==='cucker'){
    updateCucker(time);
    setText('dl-status',csFrame&&csTick<Math.round(time/csStep)?'Computing…':playing?'Playing':'Paused');
  }else setText('dl-status',valid?playing?'Playing':'Paused':'Ready');
  syncTime();queue();
  if(playing||mode==='cucker'&&csTick<Math.round(time/csStep)&&Boolean(csFrame)&&!csError)requestAnimationFrame(frame);
}
new ResizeObserver(resize).observe(canvas);
window.addEventListener('visibilitychange',()=>{lastTick=null;});
if(mode==='system')setText('dl-graph-label','Dynamical system');
else {setText('dl-graph-label','Cucker–Smale · 3D');cuckerReset();}
syncTime();resize();queue();
