import {
  EQUATIONS, derivative, eulerSolve, rk4Solve,
  parameterPoint, nearestParameterTime, estimateDifference,
} from './math.mjs';
import { PixelPainter } from './pixel.mjs';
import { compileLatex } from './latex.mjs';

const app = document.getElementById('euler-lab');
if (!app) throw new Error('Euler Lab root not found');
const $ = id => app.querySelector(`#${id}`);
const canvas = $('em-canvas');
const ctx = canvas.getContext('2d');
const staticCanvas = document.createElement('canvas');
const staticContext = staticCanvas.getContext('2d');
const pixelCanvas = document.createElement('canvas');
const pixelContext = pixelCanvas.getContext('2d');
const trailCanvas = document.createElement('canvas');
const trailContext = trailCanvas.getContext('2d');
if (!ctx || !staticContext || !pixelContext || !trailContext) throw new Error('Canvas 2D is not supported by this browser.');

const DEFAULT = Object.freeze({
  equation: 1, eqLatex: 'y^2(y^2-4)',
  paramX: String.raw`\sin(4t)(e-2\cos(18t))`,
  paramY: String.raw`\cos(5t)(e-2\cos(11t))`,
  x0: 0, y0: 0.5, h: 0.1,
  cx: 0, cy: 0, zoom: 60,
  time: 0, speed: 1, playing: false, trace: false,
  showField: true, showEuler: true, showRK4: false, showParam: true,
  renderStyle: 'pixel', pixelSize: 1,
});

let state = { ...DEFAULT };
let viewport = { width: 800, height: 540, dpr: 1 };
let dirty = true;
let queued = false;
let lastFrameTime = null;
let pointerDrag = null;
let ignoreNextClick = false;
let clickSeekTimer = null;
let trail = [];
let paramSamples = [];
let paramRevision = 0;
let sampledRevision = -1;
let derivativeFn = compileLatex(DEFAULT.eqLatex, ['x','y']);
let paramXFn = compileLatex(DEFAULT.paramX, ['t']);
let paramYFn = compileLatex(DEFAULT.paramY, ['t']);
let eqTimer = null;
let paramTimer = null;

const formatNumber = n => {
  if (!Number.isFinite(n)) return '—';
  if (Math.abs(n) >= 10000 || (Math.abs(n) < 0.001 && n !== 0)) return n.toExponential(2);
  return n.toFixed(3).replace(/\.?0+$/, '');
};
const clamp = (n, min, max) => Math.max(min, Math.min(max, n));
const equationFunction = (x, y) => derivativeFn(x,y);
const parameterPointCustom = t => ({x:paramXFn(t), y:paramYFn(t)});
const LINE_PT = 4 / 3; // 1 CSS pt = 1.333 CSS px; pixel mode is a crisp 1-pixel approximation.

function inputError(id, text) {
  $(id).textContent = text;
  $(id).hidden = !text;
}
function setEquation(text, preset = false) {
  try {
    const f = compileLatex(text, ['x','y']);
    derivativeFn = f;
    state.eqLatex = text;
    if(!preset)state.equation=0;
    inputError('em-equation-error', '');
    syncEquation();
    redrawStatic();
    return true;
  } catch(error) {
    inputError('em-equation-error', error.message);
    return false; // Keep plotting the last valid formula.
  }
}
function setParameterFormulas(xText, yText) {
  try {
    const fx=compileLatex(xText,['t']);
    const fy=compileLatex(yText,['t']);
    paramXFn=fx;paramYFn=fy;
    state.paramX=xText;state.paramY=yText;
    paramRevision++;trail=[];
    inputError('em-param-error','');
    redrawStatic();requestFrame();
    return true;
  } catch(error) {
    inputError('em-param-error',error.message);
    return false; // Atomic: old x(t), y(t) remain active together.
  }
}
function nearestParameterTimeCustom(x,y){
  ensureParamSamples();
  let bestT=0, best=Infinity;
  for(let i=0;i<paramSamples.length;i++){
    const p=paramSamples[i];if(!Number.isFinite(p.x)||!Number.isFinite(p.y))continue;
    const d=(p.x-x)**2+(p.y-y)**2;
    if(d<best){best=d;bestT=i/50;}
  }
  return {t:bestT,distance:Math.sqrt(best)};
}

function message(text = '') { $('em-message').textContent = text; }
function syncEquation() {
  $('em-equation').value = state.equation===0?'custom':String(state.equation);
  $('em-formula').textContent = 'dy/dx = '+state.eqLatex;
  $('em-equation-overlay').textContent = 'dy/dx = '+(state.eqLatex.length>38 ? state.eqLatex.slice(0,38)+'…' : state.eqLatex);
  $('em-equation-overlay').title = 'dy/dx = '+state.eqLatex;
}
function syncStep() {
  $('em-step').value = String(Number(state.h.toPrecision(5)));
  $('em-step-range').value = String(Math.log10(state.h));
}
function syncPlayback() {
  $('em-time').value = String(state.time);
  $('em-time-value').textContent = state.time.toFixed(3);
  $('em-play').textContent = state.playing ? 'Ⅱ Pause' : '▶ Play';
  $('em-live').textContent = state.playing ? 'Playing' : 'Paused';
  $('em-live').classList.toggle('is-playing', state.playing);
}
function syncUI() {
  syncEquation(); syncStep(); syncPlayback();
  $('em-x0').value = String(state.x0);
  $('em-y0').value = String(state.y0);
  $('em-speed').value = String(state.speed);
  $('em-show-field').checked = state.showField;
  $('em-show-euler').checked = state.showEuler;
  $('em-show-rk4').checked = state.showRK4;
  $('em-show-parameter').checked = state.showParam;
  $('em-trace').checked = state.trace;
  $('em-equation-latex').value=state.eqLatex;
  $('em-param-x').value=state.paramX;
  $('em-param-y').value=state.paramY;
  $('em-render-style').value = state.renderStyle;

  $('em-render-label').textContent = state.renderStyle === 'pixel'
    ? 'Pixel · 1px dots' : 'Smooth · 1pt';
  $('em-zoom').textContent = `${formatNumber(state.zoom)} px / unit`;
}
function redrawStatic() { dirty = true; requestFrame(); }
function requestFrame() {
  if (queued) return;
  queued = true;
  requestAnimationFrame(frame);
}
function toPixel(x, y) {
  return {x: viewport.width / 2 + (x - state.cx) * state.zoom,
          y: viewport.height / 2 - (y - state.cy) * state.zoom};
}
function toWorld(x, y) {
  return {x: (x - viewport.width / 2) / state.zoom + state.cx,
          y: (viewport.height / 2 - y) / state.zoom + state.cy};
}
function bounds() {
  return {
    left: state.cx - viewport.width / (2 * state.zoom),
    right: state.cx + viewport.width / (2 * state.zoom),
    bottom: state.cy - viewport.height / (2 * state.zoom),
    top: state.cy + viewport.height / (2 * state.zoom),
  };
}
function preferredGridUnit() {
  const target = 72 / state.zoom;
  const ten = 10 ** Math.floor(Math.log10(target));
  const ratio = target / ten;
  return (ratio <= 1 ? 1 : ratio <= 2 ? 2 : ratio <= 5 ? 5 : 10) * ten;
}
function drawGrid(g) {
  const b = bounds();
  const unit = preferredGridUnit();
  const xStart = Math.floor(b.left / unit);
  const xEnd = Math.ceil(b.right / unit);
  const yStart = Math.floor(b.bottom / unit);
  const yEnd = Math.ceil(b.top / unit);
  g.lineWidth = LINE_PT;
  g.strokeStyle = '#e7eef5';
  g.beginPath();
  for (let i=xStart; i<=xEnd; i++) {
    const x=toPixel(i*unit,0).x;
    g.moveTo(x, 0); g.lineTo(x, viewport.height);
  }
  for (let j=yStart; j<=yEnd; j++) {
    const y=toPixel(0,j*unit).y;
    g.moveTo(0,y); g.lineTo(viewport.width,y);
  }
  g.stroke();
  g.strokeStyle = '#8797ac'; g.lineWidth = LINE_PT;
  const origin=toPixel(0,0);
  g.beginPath();
  g.moveTo(origin.x,0); g.lineTo(origin.x,viewport.height);
  g.moveTo(0,origin.y); g.lineTo(viewport.width,origin.y); g.stroke();
  g.font='11px ui-monospace, Menlo, Consolas, monospace';
  g.fillStyle='#8899af';
  for(let i=xStart; i<=xEnd; i++) {
    const val=i*unit, p=toPixel(val,0);
    if(Math.abs(val)<unit*0.01 || p.x<14 || p.x>viewport.width-20) continue;
    g.fillText(formatNumber(val),p.x+3,clamp(origin.y+15,14,viewport.height-8));
  }
  for(let j=yStart; j<=yEnd; j++) {
    const val=j*unit, p=toPixel(0,val);
    if(Math.abs(val)<unit*0.01 || p.y<14 || p.y>viewport.height-10) continue;
    g.fillText(formatNumber(val),clamp(origin.x+7,7,viewport.width-43),p.y-4);
  }
}
function drawDirectionField(g) {
  const gap = 64;
  const len = 18;
  g.lineWidth=LINE_PT;
  g.strokeStyle='rgba(83,112,162,.38)';
  g.fillStyle='rgba(83,112,162,.50)';
  for(let sy=gap*.55; sy<viewport.height; sy+=gap) {
    for(let sx=gap*.6; sx<viewport.width; sx+=gap) {
      const world=toWorld(sx,sy);
      const slope=equationFunction(world.x,world.y);
      if (!Number.isFinite(slope)) continue;
      // Normalised tangent: (1, f(x,y)).
      const length = Math.hypot(1,slope);
      const ux=1/length, uy=-slope/length;
      const x0=sx - ux*len/2, y0=sy-uy*len/2;
      const x1=sx + ux*len/2, y1=sy+uy*len/2;
      g.beginPath(); g.moveTo(x0,y0); g.lineTo(x1,y1); g.stroke();
      const arrow=3.4;
      g.beginPath();
      g.moveTo(x1,y1);
      g.lineTo(x1-ux*arrow-uy*arrow*.65,y1-uy*arrow+ux*arrow*.65);
      g.lineTo(x1-ux*arrow+uy*arrow*.65,y1-uy*arrow-ux*arrow*.65);
      g.closePath(); g.fill();
    }
  }
}
// A pixel-perfect alternative to the browser's smoothed path strokes.
// Rendering arithmetic is kept separate from the ODE numerical method.
function pixelPainter(g) {
  return new PixelPainter(g, viewport.width, viewport.height, state.pixelSize);
}
function drawPixelPolyline(painter, points, color, dash = 0) {
  let last = null;
  for (const p of points) {
    if (!Number.isFinite(p.x) || !Number.isFinite(p.y)) { last = null; continue; }
    const current = toPixel(p.x, p.y);
    if (Math.abs(current.x) > 1e6 || Math.abs(current.y) > 1e6) { last = null; continue; }
    if (last) painter.line(last.x,last.y,current.x,current.y,color,dash);
    else painter.point(current.x,current.y,color,0);
    last = current;
  }
}
function drawPixelDirectionField(painter) {
  // Denser cobalt-blue arrows and tiny square arrowheads mimic the SFML view.
  const gap = 37;
  const len = 23;
  const ink = '#193cff';
  for (let sy=gap/2; sy<viewport.height; sy+=gap) {
    for (let sx=gap/2; sx<viewport.width; sx+=gap) {
      const world=toWorld(sx,sy);
      const slope=equationFunction(world.x,world.y);
      if (!Number.isFinite(slope)) continue;
      const m=Math.hypot(1,slope);
      const ux=1/m, uy=-slope/m;
      const x0=sx-ux*len/2, y0=sy-uy*len/2;
      const x1=sx+ux*len/2, y1=sy+uy*len/2;
      painter.line(x0,y0,x1,y1,ink);
      // Two un-antialiased prongs, each a handful of integer pixels.
      const head=5.5, side=2.7;
      painter.line(x1,y1,x1-ux*head-uy*side,y1-uy*head+ux*side,ink);
      painter.line(x1,y1,x1-ux*head+uy*side,y1-uy*head-ux*side,ink);
    }
  }
}
function compositePixels(destination, source) {
  destination.save();
  destination.imageSmoothingEnabled=false; // nearest-neighbor upscale
  destination.drawImage(source,0,0,viewport.width,viewport.height);
  destination.restore();
}
function resizePixelLayers() {
  const w=Math.max(1,Math.ceil(viewport.width/state.pixelSize));
  const h=Math.max(1,Math.ceil(viewport.height/state.pixelSize));
  for(const canvas of [pixelCanvas,trailCanvas]){
    canvas.width=w;
    canvas.height=h;
  }
}
function drawPolyline(g, points, color, lineWidth, dash = []) {
  if(points.length<2) return;
  g.beginPath();
  g.strokeStyle=color; g.lineWidth=LINE_PT;
  g.lineCap='round'; g.lineJoin='round';
  g.setLineDash(dash);
  let drawing=false;
  for (const p of points) {
    if (!Number.isFinite(p.x) || !Number.isFinite(p.y)) { drawing=false; continue; }
    const s=toPixel(p.x,p.y);
    // Offscreen extremes can form visual artifacts when a solution diverges.
    if(Math.abs(s.x)>1e6 || Math.abs(s.y)>1e6){drawing=false;continue;}
    if(!drawing) {g.moveTo(s.x,s.y);drawing=true;}
    else g.lineTo(s.x,s.y);
  }
  g.stroke(); g.setLineDash([]);
}
function ensureParamSamples() {
  if (sampledRevision === paramRevision) return;
  paramSamples=[];
  for(let i=0;i<=5000;i++){
    const t=i/50;
    paramSamples.push(parameterPointCustom(t));
  }
  sampledRevision=paramRevision;
}
function drawMarker(g,x,y,color,r=5) {
  const p=toPixel(x,y);
  if(p.x < -20 || p.x>viewport.width+20 || p.y < -20 || p.y>viewport.height+20)return;
  g.beginPath();g.arc(p.x,p.y,r,0,Math.PI*2);
  g.fillStyle='#fff';g.fill();g.lineWidth=LINE_PT;g.strokeStyle=color;g.stroke();
}
function drawStaticLayer() {
  const g=staticContext;
  g.clearRect(0,0,viewport.width,viewport.height);
  g.fillStyle='#fbfdff';g.fillRect(0,0,viewport.width,viewport.height);
  drawGrid(g);
  const pixel=state.renderStyle==='pixel';
  const painter=pixel?pixelPainter(pixelContext):null;
  if(pixel)pixelContext.clearRect(0,0,pixelCanvas.width,pixelCanvas.height);
  if(state.showField){
    if(pixel)drawPixelDirectionField(painter);
    else drawDirectionField(g);
  }
  const b=bounds();
  const end=Math.min(b.right+0.15, state.x0 + 300);
  const e=eulerSolve(equationFunction,state.x0,state.y0,state.h,end);
  let r=null;
  if(state.showRK4){
    r=rk4Solve(equationFunction,state.x0,state.y0,Math.min(state.h/4,0.025),end);
    if(pixel)drawPixelPolyline(painter,r.points,'#285dd9',7);
    else drawPolyline(g,r.points,'#397fc2',LINE_PT,[6,5]);
  }
  if(state.showEuler){
    if(pixel)drawPixelPolyline(painter,e.points,'#f53742');
    else drawPolyline(g,e.points,'#d35253',LINE_PT);
  }
  if(state.showParam) {
    ensureParamSamples();
    if(pixel)drawPixelPolyline(painter,paramSamples,'#069b7d');
    else drawPolyline(g,paramSamples,'rgba(0,143,111,.60)',LINE_PT);
  }
  if(pixel)compositePixels(g,pixelCanvas);
  if(state.showEuler||state.showRK4)drawMarker(g,state.x0,state.y0,'#b34b52',4.1);
  const endpoint=e.points.at(-1);
  $('em-stat-steps').textContent=String(e.points.length-1);
  $('em-stat-endpoint').textContent=endpoint?`(${formatNumber(endpoint.x)}, ${formatNumber(endpoint.y)})`:'—';
  $('em-stat-difference').textContent=r?formatNumber(estimateDifference(e.points,r.points)):'—';
  if (e.stopped) message('The numerical curve stopped at a divergence or step limit. Reduce h or change the initial value.');
  else if($('em-message').textContent.startsWith('The numerical curve stopped')) message('');
  dirty=false;
}
function drawDynamicLayer() {
  if(!state.showParam)return;
  if(state.trace && trail.length>=2) {
    if(state.renderStyle==='pixel'){
      trailContext.clearRect(0,0,trailCanvas.width,trailCanvas.height);
      drawPixelPolyline(pixelPainter(trailContext),trail,'#d19b31');
      compositePixels(ctx,trailCanvas);
    } else drawPolyline(ctx,trail,'#d19b31',LINE_PT);
  }
  const p=parameterPointCustom(state.time);
  drawMarker(ctx,p.x,p.y,'#1e3449',6);
  const screen=toPixel(p.x,p.y);
  if(screen.x>=0&&screen.x<=viewport.width&&screen.y>=0&&screen.y<=viewport.height){
    ctx.beginPath();ctx.arc(screen.x,screen.y,2.5,0,Math.PI*2);
    ctx.fillStyle='#1e3449';ctx.fill();
  }
}
function updateTrail(from,to){
  if(!state.trace || !state.showParam)return;
  if(to<from){ trail=[]; return; }
  const n=Math.min(300,Math.max(1,Math.ceil((to-from)/0.02)));
  for(let i=1;i<=n;i++){
    const t=from+(to-from)*i/n;
    trail.push(parameterPointCustom(t));
  }
  if(trail.length>8000) trail.splice(0,trail.length-8000);
}
function frame(now){
  queued=false;
  if(state.playing){
    const elapsed=lastFrameTime===null?0:clamp((now-lastFrameTime)/1000,0,.08);
    const previous=state.time;
    state.time=clamp(state.time+elapsed*state.speed,0,100);
    updateTrail(previous,state.time);
    syncPlayback();
    if(state.time>=100){state.playing=false; syncPlayback();}
  }
  lastFrameTime=now;
  if(dirty)drawStaticLayer();
  ctx.clearRect(0,0,viewport.width,viewport.height);
  ctx.drawImage(staticCanvas,0,0,viewport.width,viewport.height);
  drawDynamicLayer();
  if(state.playing)requestFrame();
}
function resize(){
  const rect=canvas.getBoundingClientRect();
  if(rect.width<20||rect.height<20)return;
  viewport.width=rect.width;viewport.height=rect.height;
  viewport.dpr=Math.min(window.devicePixelRatio||1,2.5);
  for(const c of [canvas,staticCanvas]){
    c.width=Math.round(rect.width*viewport.dpr);
    c.height=Math.round(rect.height*viewport.dpr);
  }
  ctx.setTransform(viewport.dpr,0,0,viewport.dpr,0,0);
  staticContext.setTransform(viewport.dpr,0,0,viewport.dpr,0,0);
  resizePixelLayers();
  redrawStatic();
}
function setInitial(x,y){
  if(!Number.isFinite(x)||!Number.isFinite(y)){message('x₀ and y₀ must be finite numbers.');return;}
  state.x0=clamp(x,-1e4,1e4);state.y0=clamp(y,-1e4,1e4);
  $('em-x0').value=formatNumber(state.x0);$('em-y0').value=formatNumber(state.y0);
  redrawStatic();
}
function setStep(h){
  if(!Number.isFinite(h)||h<=0){message('Step size h must be positive.');syncStep();return;}
  state.h=clamp(h,0.001,2);
  syncStep();redrawStatic();
}
function setZoom(zoom,px=viewport.width/2,py=viewport.height/2){
  const fixed=toWorld(px,py);
  state.zoom=clamp(zoom,12,300);
  const next=toWorld(px,py);
  state.cx+=fixed.x-next.x;state.cy+=fixed.y-next.y;
  $('em-zoom').textContent=`${formatNumber(state.zoom)} px / unit`;
  redrawStatic();
}
function setPlaying(playing){
  if(playing&&state.time>=100) setTime(0);
  state.playing=Boolean(playing);
  lastFrameTime=null;
  syncPlayback();requestFrame();
}
function setTime(value, keepTrail=false){
  state.time=clamp(Number(value),0,100);
  if(!keepTrail)trail=[];
  syncPlayback();requestFrame();
}
function resetAll(){
  state={...DEFAULT};trail=[];paramRevision++;sampledRevision=-1;
  derivativeFn=compileLatex(DEFAULT.eqLatex,['x','y']);
  paramXFn=compileLatex(DEFAULT.paramX,['t']);
  paramYFn=compileLatex(DEFAULT.paramY,['t']);
  inputError('em-equation-error','');inputError('em-param-error','');
  resizePixelLayers();
  syncUI();message('');redrawStatic();
}

// Populate exact original eight cases.
for(const e of EQUATIONS){
  const opt=document.createElement('option');
  opt.value=String(e.id);opt.textContent=`${e.id}. ${e.label}`;
  $('em-equation').append(opt);
}
const customOpt=document.createElement('option');
customOpt.value='custom';customOpt.textContent='Custom LaTeX';
$('em-equation').append(customOpt);
$('em-equation').addEventListener('change',()=>{
  const selected=$('em-equation').value;
  if(selected==='custom')return;
  const equation=EQUATIONS[Number(selected)-1];
  if(!equation)return;
  state.equation=Number(selected);
  $('em-equation-latex').value=equation.latex;
  setEquation(equation.latex,true);
});
$('em-equation-latex').addEventListener('input',()=>{
  clearTimeout(eqTimer);
  eqTimer=setTimeout(()=>setEquation($('em-equation-latex').value),150);
});
for(const id of ['em-param-x','em-param-y']) {
  $(id).addEventListener('input',()=>{
    clearTimeout(paramTimer);
    paramTimer=setTimeout(()=>setParameterFormulas($('em-param-x').value,$('em-param-y').value),150);
  });
}
$('em-param-original').addEventListener('click',()=>{
  $('em-param-x').value=DEFAULT.paramX;
  $('em-param-y').value=DEFAULT.paramY;
  setParameterFormulas(DEFAULT.paramX,DEFAULT.paramY);
});
$('em-param-fractions').addEventListener('click',()=>{
  const x=String.raw`\sin(4t)(\exp(\cos(\frac{t}{2}))-2\cos(18t)-\sin(\frac{1}{12})^5)`;
  const y=String.raw`\cos(5t)(\exp(\cos(\frac{t}{3}))-2\cos(11t)-\sin(\frac{1}{12})^5)`;
  $('em-param-x').value=x;$('em-param-y').value=y;
  setParameterFormulas(x,y);
});
for(const name of ['x0','y0']) $('em-'+name).addEventListener('change',()=>{
  setInitial(Number($('em-x0').value),Number($('em-y0').value));
});
$('em-step').addEventListener('change',()=>setStep(Number($('em-step').value)));
$('em-step-range').addEventListener('input',()=>setStep(10**Number($('em-step-range').value)));
$('em-step-down').addEventListener('click',()=>setStep(state.h/1.25));
$('em-step-up').addEventListener('click',()=>setStep(state.h*1.25));
const toggles=[['em-show-field','showField'],['em-show-euler','showEuler'],['em-show-rk4','showRK4'],['em-show-parameter','showParam'],['em-trace','trace']];
for(const [id,key] of toggles){
  $(id).addEventListener('change',()=>{
    state[key]=$(id).checked;
    if(key==='trace')trail=[];
    redrawStatic();
  });
}
$('em-render-style').addEventListener('change',()=>{
  state.renderStyle=$('em-render-style').value;
  syncUI();redrawStatic();
});

$('em-reset-view').addEventListener('click',()=>{
  state.cx=0;state.cy=0;state.zoom=60;syncUI();redrawStatic();
});
$('em-reset-all').addEventListener('click',resetAll);
$('em-play').addEventListener('click',()=>setPlaying(!state.playing));
$('em-rewind').addEventListener('click',()=>{setPlaying(false);setTime(0);});
$('em-time').addEventListener('input',()=>{setPlaying(false);setTime($('em-time').value);});
$('em-speed').addEventListener('change',()=>{state.speed=Number($('em-speed').value);});

// Mouse + touch: pan, zoom, set initial value, seek parametric time.
canvas.addEventListener('pointerdown',event=>{
  if(event.button!==0&&event.pointerType==='mouse')return;
  pointerDrag={startX:event.offsetX,startY:event.offsetY, cx:state.cx,cy:state.cy,moved:false};
  canvas.setPointerCapture(event.pointerId);
});
canvas.addEventListener('pointermove',event=>{
  const world=toWorld(event.offsetX,event.offsetY);
  $('em-cursor').textContent=`x: ${formatNumber(world.x)} · y: ${formatNumber(world.y)}`;
  if(!pointerDrag)return;
  const dx=event.offsetX-pointerDrag.startX;
  const dy=event.offsetY-pointerDrag.startY;
  if(Math.hypot(dx,dy)>4)pointerDrag.moved=true;
  if(!pointerDrag.moved)return;
  canvas.classList.add('is-dragging');
  state.cx=pointerDrag.cx-dx/state.zoom;
  state.cy=pointerDrag.cy+dy/state.zoom;
  redrawStatic();
});
canvas.addEventListener('pointerup',()=>{
  const prev=pointerDrag;
  pointerDrag=null;
  canvas.classList.remove('is-dragging');
  ignoreNextClick = Boolean(prev?.moved);
});
canvas.addEventListener('pointercancel',()=>{
  pointerDrag=null;canvas.classList.remove('is-dragging');
});
canvas.addEventListener('click',event=>{
  if(ignoreNextClick){ignoreNextClick=false;return;}
  if(event.detail !== 1 || !state.showParam)return;
  // Wait until the browser's double-click window has passed. Seeking on
  // pointerup incorrectly changed t just before a double-click set (x0,y0).
  const px=event.offsetX, py=event.offsetY;
  if(clickSeekTimer !== null)clearTimeout(clickSeekTimer);
  clickSeekTimer=setTimeout(()=>{
    clickSeekTimer=null;
    const world=toWorld(px,py);
    const seek=nearestParameterTimeCustom(world.x,world.y);
    if(seek.distance*state.zoom<=14){
      setPlaying(false);setTime(seek.t);
      message(`Moved to t ≈ ${seek.t.toFixed(2)} on the parametric curve.`);
    }
  },400);
});
canvas.addEventListener('dblclick',event=>{
  event.preventDefault();
  if(clickSeekTimer !== null){clearTimeout(clickSeekTimer);clickSeekTimer=null;}
  const world=toWorld(event.offsetX,event.offsetY);
  setInitial(world.x,world.y);
  message(`Initial value set to (${formatNumber(world.x)}, ${formatNumber(world.y)}).`);
});
canvas.addEventListener('wheel',event=>{
  event.preventDefault();
  setZoom(state.zoom*Math.exp(-event.deltaY*.0028),event.offsetX,event.offsetY);
},{passive:false});

// Original keyboard controls, but do not intercept typing into inputs/selects.
document.addEventListener('keydown',event=>{
  if(event.metaKey||event.ctrlKey||event.altKey)return;
  const target=event.target;
  if(target instanceof HTMLElement && target.closest('input,select,textarea,button,[contenteditable="true"]'))return;
  const key=event.key.toLowerCase();
  let handled=true;
  if(/^[1-8]$/.test(key)){
    const e=EQUATIONS[Number(key)-1];state.equation=Number(key);
    $('em-equation-latex').value=e.latex;setEquation(e.latex,true);
  }
  else if(key==='a')setStep(state.h/1.25);
  else if(key==='d')setStep(state.h*1.25);
  else if(key==='w')setZoom(state.zoom*1.38);
  else if(key==='s')setZoom(state.zoom/1.38);
  else if(key==='f'||key===' ')setPlaying(!state.playing);
  else if(key==='t'){$('em-trace').checked=!state.trace;state.trace=!state.trace;trail=[];redrawStatic();}
  else if(key==='q'){setPlaying(false);setTime(state.time-.05);}
  else if(key==='e'){setPlaying(false);setTime(state.time+.05);}
  else if(key==='p'){
    state.renderStyle=state.renderStyle==='pixel'?'smooth':'pixel';
    syncUI();redrawStatic();
  }
  else if(key==='r')resetAll();
  else handled=false;
  if(handled)event.preventDefault();
});

syncUI();
const observer=new ResizeObserver(resize);
observer.observe(canvas);
resize();
