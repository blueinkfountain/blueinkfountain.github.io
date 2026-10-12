import {MAX_TIME} from './time-range.mjs';
import {
  EQUATIONS,
  stepToFraction, fractionToStep, nextStepSize, pointAtElapsedTime,
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
  equation: 0, eqLatex: '', method: 'rk4', order:1, v0:0, plotMode:'solution',
  paramX: '', paramY: '',
  x0: 0, y0: 0.5, h: 0.1,
  cx: 0, cy: 0, zoom: 60,
  time: 0, speed: 1, playing: false, trace: false,
  showField: true, showSolution: true, showCompare: false, showParam: true,
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
let derivativeFn = null;
let solutionCache = null;
let odeDuration = 0;
let solveWorker=null,solveKey='',solved=null;
const equationMemory={1:'',2:''};
const initialMemory={1:{x0:0,y0:.5,v0:0},2:{x0:0,y0:1,v0:0}};
const SECOND_EXAMPLES=[
  {id:'damped',label:'Damped oscillator',latex:String.raw`y''=-y-0.2y'`,y0:1,v0:0},
  {id:'harmonic',label:'Harmonic oscillator',latex:String.raw`y''=-y`,y0:1,v0:0},
];
let paramXFn = null;
let paramYFn = null;
let eqTimer = null;
let paramTimer = null;

const formatNumber = n => {
  if (!Number.isFinite(n)) return '—';
  if (Math.abs(n) >= 10000 || (Math.abs(n) < 0.001 && n !== 0)) return n.toExponential(2);
  return n.toFixed(3).replace(/\.?0+$/, '');
};
const clamp = (n, min, max) => Math.max(min, Math.min(max, n));
const equationFunction = (x, y, v=0) => derivativeFn(x,y,v);
const parameterPointCustom = t => (paramXFn && paramYFn) ? ({x:paramXFn(t), y:paramYFn(t)}) : null;
const hasParameter = () => Boolean(paramXFn && paramYFn);
const LINE_PT = 4 / 3; // 1 CSS pt = 1.333 CSS px; pixel mode is a crisp 1-pixel approximation.

function inputError(id, text) {
  $(id).textContent = text;
  $(id).hidden = !text;
}
function setEquation(text, preset = false) {
  const trimmed = text.trim();
  if (!trimmed) {
    derivativeFn = null;
    state.eqLatex = '';
    state.equation = 0;
    equationMemory[state.order]='';
    inputError('em-equation-error', '');
    syncEquation(); redrawStatic();
    return true;
  }
  try {
    const f = compileLatex(trimmed, state.order===2?['x','y','v']:['x','y']);
    derivativeFn = f;
    state.eqLatex = trimmed;
    equationMemory[state.order]=trimmed;
    if(!preset)state.equation=0;
    inputError('em-equation-error', '');
    syncEquation();redrawStatic();
    return true;
  } catch(error) {
    inputError('em-equation-error', error.message);
    return false; // Preserve last valid plot on incomplete LaTeX.
  }
}
function setParameterFormulas(xText, yText) {
  // No partial trajectory: both coordinate expressions must be present.
  if (!xText.trim() || !yText.trim()) {
    paramXFn=null;paramYFn=null;
    state.paramX=xText;state.paramY=yText;
    state.playing=false;
    paramRevision++;sampledRevision=-1;trail=[];
    inputError('em-param-error','');
    syncPlayback();redrawStatic();
    return true;
  }
  try {
    const fx=compileLatex(xText,['t']);
    const fy=compileLatex(yText,['t']);
    paramXFn=fx;paramYFn=fy;
    state.paramX=xText;state.paramY=yText;
    paramRevision++;sampledRevision=-1;trail=[];
    inputError('em-param-error','');
    syncPlayback();redrawStatic();
    return true;
  } catch(error) {
    inputError('em-param-error',error.message);
    return false; // Preserve last valid full trajectory.
  }
}
function nearestParameterTimeCustom(x,y){
  ensureParamSamples();
  let bestT=0, best=Infinity;
  for(let i=0;i<paramSamples.length;i++){
    const p=paramSamples[i];if(!Number.isFinite(p.x)||!Number.isFinite(p.y))continue;
    const d=(p.x-x)**2+(p.y-y)**2;
    if(d<best){best=d;bestT=i*MAX_TIME/20000;}
  }
  return {t:bestT,distance:Math.sqrt(best)};
}

function message(text = '') { $('em-message').textContent = text; }
function syncEquation() {
  $('em-equation').value = state.equation===0?'custom':String(state.equation);
  const overlay=$('em-equation-overlay');
  overlay.hidden=!state.eqLatex;
  overlay.textContent=state.eqLatex ? `${state.eqLatex.includes('=')?'':state.order===2?'y″ = ':'y′ = '}${state.eqLatex.slice(0,36)}${state.eqLatex.length>36?'…':''}` : '';
  overlay.title=state.eqLatex;
}
function syncStep() {
  $('em-step').value = String(Number(state.h.toPrecision(5)));
  $('em-step-range').value = String(Math.round(stepToFraction(state.h)*1000));
}
// The timeline controls BOTH numerical ODE trajectories and parametric curves.
// For an ODE-only plot, its endpoint is the last successfully integrated x.
function timelineMax() {
  return hasParameter() ? MAX_TIME : odeDuration;
}
function canSeekTime() {
  return hasParameter() || (Boolean(derivativeFn) && odeDuration > 0);
}
function syncPlayback() {
  const max = timelineMax();
  if (state.time > max) state.time = max;
  const slider = $('em-time');
  slider.max = String(Math.max(max, 0.001));
  slider.value = String(state.time);
  slider.disabled = !canSeekTime();
  $('em-time-value').textContent = state.time.toFixed(3);
  $('em-play').textContent = state.playing ? 'Ⅱ Pause' : '▶ Play';
  $('em-live').textContent = !canSeekTime() ? 'Ready' : state.playing ? 'Playing' : 'Paused';
  $('em-live').classList.toggle('is-playing', state.playing);
  $('em-play').disabled = !canSeekTime();
  $('em-time').setAttribute('aria-valuetext', `${state.time.toFixed(3)} / ${max.toFixed(3)}`);
}
function syncUI() {
  syncEquation(); syncStep(); syncPlayback();
  $('em-x0').value = String(state.x0);
  $('em-y0').value = String(state.y0);
  $('em-v0').value = String(state.v0);
  $('em-plot-mode').value=state.plotMode;
  $('em-v0-row').hidden=state.order!==2;
  $('em-plot-mode-row').hidden=state.order!==2;
  $('em-equation-label').textContent=state.order===2?'LaTeX · y″ = F(x, y, y′)':'LaTeX · y′ = f(x, y)';
  $('em-order-first').classList.toggle('is-selected',state.order===1);
  $('em-order-second').classList.toggle('is-selected',state.order===2);
  $('em-order-first').setAttribute('aria-pressed',String(state.order===1));
  $('em-order-second').setAttribute('aria-pressed',String(state.order===2));
  $('em-show-field').disabled=state.order===2;
  $('em-show-field').closest('label').hidden=state.order===2;
  $('em-speed').value = String(state.speed);
  $('em-show-field').checked = state.showField;
  $('em-method').value = state.method;
  $('em-show-solution').checked = state.showSolution;
  $('em-show-compare').checked = state.showCompare;
  $('em-compare-label').textContent = state.method === 'rk4' ? 'Euler comparison' : 'RK4 comparison';
  $('em-show-parameter').checked = state.showParam;
  $('em-trace').checked = state.trace;
  $('em-equation-latex').value=state.eqLatex;
  $('em-param-x').value=state.paramX;
  $('em-param-y').value=state.paramY;
  $('em-render-style').value = state.renderStyle;

  $('em-zoom').textContent = `${formatNumber(state.zoom)} px/unit`;
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
  if (hasParameter()) {
    for(let i=0;i<=20000;i++){
      const t=i*MAX_TIME/20000;
      const point=parameterPointCustom(t);
      paramSamples.push(point && Number.isFinite(point.x) && Number.isFinite(point.y) ? point : {x:NaN,y:NaN});
    }
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
  if(state.order===1 && state.showField && derivativeFn){
    if(pixel)drawPixelDirectionField(painter);
    else drawDirectionField(g);
  }
  let solution=null;
  let comparison=null;
  if(derivativeFn){
    const phase=state.order===2 && state.plotMode==='phase';
    const key=JSON.stringify([state.eqLatex,state.order,state.x0,state.y0,state.v0,state.h,state.method,state.showCompare]);
    if(key!==solveKey){
      solveKey=key;solved=null;solveWorker?.terminate();
      solveWorker=new Worker(new URL('./solver-worker.mjs',import.meta.url),{type:'module'});
      message('Computing numerical solution…');
      solveWorker.onmessage=({data})=>{
        if(data.error){message(data.error);return;}
        solved=data;message('');redrawStatic();
      };
      solveWorker.onerror=()=>message('Unable to compute numerical solution.');
      solveWorker.postMessage({kind:'scalar',expression:state.eqLatex,order:state.order,x0:state.x0,y0:state.y0,v0:state.v0,h:state.h,method:state.method,compare:state.showCompare});
    }
    solution=solved?.solution??null;comparison=solved?.comparison??null;
    const projected=pts=>phase?pts.map(p=>({x:p.y,y:p.v})):pts;
    if(comparison){
      if(pixel)drawPixelPolyline(painter,projected(comparison.points),'#285dd9',7);
      else drawPolyline(g,projected(comparison.points),'#397fc2',LINE_PT,[6,5]);
    }
    if(state.showSolution && solution){
      if(pixel)drawPixelPolyline(painter,projected(solution.points),'#f53742');
      else drawPolyline(g,projected(solution.points),'#d35253',LINE_PT);
    }
  }
  if(state.showParam && hasParameter()) {
    ensureParamSamples();
    if(pixel)drawPixelPolyline(painter,paramSamples,'#069b7d');
    else drawPolyline(g,paramSamples,'rgba(0,143,111,.60)',LINE_PT);
  }
  // Reuse numerical points during scrubbing: the slider never reintegrates
  // the differential equation on each pointer movement.
  solutionCache=solution;
  odeDuration=solution && solution.points.length>1
    ? Math.max(0,solution.points.at(-1).x-state.x0) : 0;
  syncPlayback();
  if(pixel)compositePixels(g,pixelCanvas);
  if(solution)drawMarker(g,state.order===2&&state.plotMode==='phase'?state.y0:state.x0,state.order===2&&state.plotMode==='phase'?state.v0:state.y0,'#b34b52',4.1);
  const endpoint=solution?.points.at(-1);
  $('em-stat-steps').textContent=solution?`${state.method==='rk4'?'RK4':'Euler'} · ${solution.steps} steps`:'';
  $('em-stat-endpoint').textContent=endpoint?`(${formatNumber(endpoint.x)}, ${formatNumber(endpoint.y)}${state.order===2?', '+formatNumber(endpoint.v):''})`:'';
  if(solution?.stopped) message('Numerical solution stopped at a step limit or divergence.');
  else if($('em-message').textContent.startsWith('Numerical solution stopped')) message('');
  dirty=false;
}
// Integration step size is draggable directly inside the graph.
// A separate range input in the sidebar shares the EXACT same state.h.
function stepRuler(){
  const left=19,right=Math.min(224,viewport.width-25),y=viewport.height-34;
  return {left,right,y,handle:left+(right-left)*stepToFraction(state.h)};
}
function stepFromPixel(px){
  const {left,right}=stepRuler();
  return fractionToStep((px-left)/Math.max(1,right-left));
}
function isOnStepRuler(px,py){
  if(!derivativeFn)return false;
  const {left,right,y}=stepRuler();
  return px>=left-9&&px<=right+9&&Math.abs(py-y)<=19;
}
function drawStepRuler(g){
  if(!derivativeFn)return;
  const {left,right,y,handle}=stepRuler();
  g.save();
  g.fillStyle='rgba(255,255,255,.94)';g.fillRect(left-12,y-28,right-left+30,49);
  g.font='11px ui-monospace, Menlo, Consolas, monospace';
  g.fillStyle='#425e83';g.fillText('drag h  '+formatNumber(state.h),left,y-10);
  g.lineWidth=1;g.strokeStyle='#b6cce2';g.beginPath();g.moveTo(left,y+7);g.lineTo(right,y+7);g.stroke();
  g.fillStyle='#2459a8';g.beginPath();g.arc(handle,y+7,6,0,2*Math.PI);g.fill();
  g.restore();
}
function drawDynamicLayer() {
  // Current position along the NUMERICAL solution. This gives the timeline
  // an immediately visible effect even with both parametric fields blank.
  if(state.showSolution && solutionCache && state.time > 0) {
    const p=pointAtElapsedTime(solutionCache.points,state.time);
    if(p) {
      const phase=state.order===2 && state.plotMode==='phase';
      drawMarker(ctx,phase?p.y:p.x,phase?p.v:p.y,'#d62f45',6);
    }
  }
  if(!state.showParam || !hasParameter())return;
  if(state.trace && trail.length>=2) {
    if(state.renderStyle==='pixel'){
      trailContext.clearRect(0,0,trailCanvas.width,trailCanvas.height);
      drawPixelPolyline(pixelPainter(trailContext),trail,'#d19b31');
      compositePixels(ctx,trailCanvas);
    } else drawPolyline(ctx,trail,'#d19b31',LINE_PT);
  }
  const p=parameterPointCustom(state.time);
  if(!p || !Number.isFinite(p.x) || !Number.isFinite(p.y))return;
  drawMarker(ctx,p.x,p.y,'#1e3449',6);
  const screen=toPixel(p.x,p.y);
  if(screen.x>=0&&screen.x<=viewport.width&&screen.y>=0&&screen.y<=viewport.height){
    ctx.beginPath();ctx.arc(screen.x,screen.y,2.5,0,Math.PI*2);
    ctx.fillStyle='#1e3449';ctx.fill();
  }
}
function updateTrail(from,to){
  if(!state.trace || !state.showParam || !hasParameter())return;
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
    state.time=clamp(state.time+elapsed*state.speed,0,timelineMax());
    updateTrail(previous,state.time);
    syncPlayback();
    if(state.time>=timelineMax()){state.playing=false; syncPlayback();}
  }
  lastFrameTime=now;
  if(dirty)drawStaticLayer();
  ctx.clearRect(0,0,viewport.width,viewport.height);
  ctx.drawImage(staticCanvas,0,0,viewport.width,viewport.height);
  drawDynamicLayer();
  drawStepRuler(ctx);
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
function setInitial(x,y,v=state.v0){
  if(!Number.isFinite(x)||!Number.isFinite(y)){message('x₀ and y₀ must be finite numbers.');return;}
  state.x0=clamp(x,-1e4,1e4);state.y0=clamp(y,-1e4,1e4);state.v0=clamp(v,-1e4,1e4);
  initialMemory[state.order]={x0:state.x0,y0:state.y0,v0:state.v0};
  $('em-x0').value=formatNumber(state.x0);$('em-y0').value=formatNumber(state.y0);$('em-v0').value=formatNumber(state.v0);
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
  $('em-zoom').textContent=`${formatNumber(state.zoom)} px/unit`;
  redrawStatic();
}
function setPlaying(playing){
  if(playing && !canSeekTime())return;
  if(playing&&state.time>=timelineMax()) setTime(0);
  state.playing=Boolean(playing);
  lastFrameTime=null;
  syncPlayback();requestFrame();
}
function setTime(value, keepTrail=false){
  const time=Number(value);
  if(!Number.isFinite(time))return;
  state.time=clamp(time,0,timelineMax());
  if(!keepTrail)trail=[];
  syncPlayback();requestFrame();
}
function resetAll(){
  state={...DEFAULT};trail=[];paramRevision++;sampledRevision=-1;
  equationMemory[1]='';equationMemory[2]='';
  initialMemory[1]={x0:0,y0:.5,v0:0};initialMemory[2]={x0:0,y0:1,v0:0};
  derivativeFn=null;paramXFn=null;paramYFn=null;
  solutionCache=null;odeDuration=0;solveWorker?.terminate();solveKey='';solved=null;
  inputError('em-equation-error','');inputError('em-param-error','');
  resizePixelLayers();
  populateEquationOptions();syncUI();message('');redrawStatic();
}

// Each ODE order has its own examples. Custom remains the default on page load.
function populateEquationOptions(){
  $('em-equation').replaceChildren();
  const custom=document.createElement('option');custom.value='custom';custom.textContent='Custom';
  $('em-equation').append(custom);
  const options=state.order===1?EQUATIONS:SECOND_EXAMPLES;
  for(const e of options){
    const opt=document.createElement('option');
    opt.value=String(e.id);opt.textContent=state.order===1?`${e.id}. ${e.label}`:e.label;
    $('em-equation').append(opt);
  }
  syncEquation();
}
function setOrder(order){
  if(order===state.order)return;
  initialMemory[state.order]={x0:state.x0,y0:state.y0,v0:state.v0};
  state.order=order;state.equation=0;state.plotMode='solution';
  ({x0:state.x0,y0:state.y0,v0:state.v0}=initialMemory[order]);
  state.eqLatex=equationMemory[order];
  derivativeFn=null;
  if(state.eqLatex){
    try{derivativeFn=compileLatex(state.eqLatex,order===2?['x','y','v']:['x','y']);}
    catch{state.eqLatex='';equationMemory[order]='';}
  }
  populateEquationOptions();syncUI();
  inputError('em-equation-error','');message('');redrawStatic();
}
$('em-order-first').addEventListener('click',()=>setOrder(1));
$('em-order-second').addEventListener('click',()=>setOrder(2));
$('em-equation').addEventListener('change',()=>{
  const selected=$('em-equation').value;
  if(selected==='custom'){
    $('em-equation-latex').focus();return;
  }
  const equation=state.order===1?EQUATIONS[Number(selected)-1]:SECOND_EXAMPLES.find(e=>e.id===selected);
  if(!equation)return;
  state.equation=equation.id;
  if(state.order===2)setInitial(state.x0,equation.y0,equation.v0);
  $('em-equation-latex').value=equation.latex;
  setEquation(equation.latex,true);
});
populateEquationOptions();
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
for(const name of ['x0','y0','v0']) $('em-'+name).addEventListener('change',()=>{
  setInitial(Number($('em-x0').value),Number($('em-y0').value),Number($('em-v0').value));
});
$('em-step').addEventListener('change',()=>setStep(Number($('em-step').value)));
$('em-step-range').addEventListener('input',()=>setStep(fractionToStep(Number($('em-step-range').value)/1000)));
$('em-plot-mode').addEventListener('change',()=>{state.plotMode=$('em-plot-mode').value;redrawStatic();});
$('em-step-down').addEventListener('click',()=>setStep(nextStepSize(state.h,1/1.25)));
$('em-step-up').addEventListener('click',()=>setStep(nextStepSize(state.h,1.25)));
const toggles=[['em-show-field','showField'],['em-show-solution','showSolution'],['em-show-compare','showCompare'],['em-show-parameter','showParam'],['em-trace','trace']];
for(const [id,key] of toggles){
  $(id).addEventListener('change',()=>{
    state[key]=$(id).checked;
    if(key==='trace')trail=[];
    redrawStatic();
  });
}
$('em-method').addEventListener('change',()=>{
  state.method=$('em-method').value;
  syncUI();redrawStatic();
});
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
$('em-time').addEventListener('pointerdown',()=>setPlaying(false));
$('em-time').addEventListener('input',()=>{
  // Snapshot the native thumb position BEFORE syncPlayback writes to the range.
  const requested=Number($('em-time').value);
  setPlaying(false);setTime(requested);
});
$('em-speed').addEventListener('change',()=>{state.speed=Number($('em-speed').value);});

// Mouse + touch: pan, zoom, set initial value, seek parametric time.
canvas.addEventListener('pointerdown',event=>{
  if(event.button!==0&&event.pointerType==='mouse')return;
  if(isOnStepRuler(event.offsetX,event.offsetY)){
    pointerDrag={mode:'step',moved:false};
    canvas.setPointerCapture(event.pointerId);
    setStep(stepFromPixel(event.offsetX));
    canvas.classList.add('is-step-dragging');
    return;
  }
  pointerDrag={startX:event.offsetX,startY:event.offsetY, cx:state.cx,cy:state.cy,moved:false};
  canvas.setPointerCapture(event.pointerId);
});
canvas.addEventListener('pointermove',event=>{
  const world=toWorld(event.offsetX,event.offsetY);
  $('em-cursor').textContent=`x: ${formatNumber(world.x)} · y: ${formatNumber(world.y)}`;
  if(!pointerDrag)return;
  if(pointerDrag.mode==='step'){
    pointerDrag.moved=true;setStep(stepFromPixel(event.offsetX));return;
  }
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
  canvas.classList.remove('is-step-dragging');
  ignoreNextClick = Boolean(prev?.moved);
});
canvas.addEventListener('pointercancel',()=>{
  pointerDrag=null;canvas.classList.remove('is-dragging');canvas.classList.remove('is-step-dragging');
});
canvas.addEventListener('click',event=>{
  if(ignoreNextClick){ignoreNextClick=false;return;}
  if(event.detail !== 1 || !state.showParam || !hasParameter())return;
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
  if(state.order===2 && state.plotMode==='phase')setInitial(state.x0,world.x,world.y);
  else setInitial(world.x,world.y);
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
    if(state.order===1){const e=EQUATIONS[Number(key)-1];state.equation=Number(key);
    $('em-equation-latex').value=e.latex;setEquation(e.latex,true);}
    else handled=false;
  }
  else if(key==='a')setStep(nextStepSize(state.h,1/1.25));
  else if(key==='d')setStep(nextStepSize(state.h,1.25));
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
