/** Numerical engines for vector-valued ODEs and Cucker–Smale agents.
 * No DOM, eval, server, or external dependency. All state is local.
 */
export const MAX_STATE = 1e8;
const finiteVector = v => Array.isArray(v) && v.every(Number.isFinite);

/** y'=f(t,y), dimension 2 or 3. All RK4 stages update the WHOLE vector. */
export function integrateSystem(f, initial, {
  t0 = 0, tMax = 20, h = 0.02, method = 'rk4', maxSteps = 20000,
} = {}) {
  if (!finiteVector(initial) || ![2, 3].includes(initial.length)) throw new RangeError('Initial state must have 2 or 3 finite entries.');
  if (![t0, tMax, h].every(Number.isFinite) || !(h > 0) || tMax < t0) throw new RangeError('Provide finite t₀ ≤ tMax and h > 0.');
  if (!['rk4', 'euler'].includes(method)) throw new RangeError('Select RK4 or Euler.');
  if (!Number.isInteger(maxSteps) || maxSteps < 1) throw new RangeError('maxSteps must be positive.');
  let time = t0, state = initial.slice();
  const points = [{t:time, values:state.slice()}];
  let stopped = false, reason = '';
  function deriv(t, v) {
    const out = f(t, v);
    if (!finiteVector(out) || out.length !== state.length) throw new RangeError('The vector field returned an invalid derivative.');
    return out;
  }
  for (let count=0; count<maxSteps && time<tMax-1e-12; count++) {
    const dt=Math.min(h, tMax-time);
    let next;
    try {
      const k1=deriv(time,state);
      if(method==='euler') next=state.map((v,i)=>v+dt*k1[i]);
      else {
        const k2=deriv(time+dt/2,state.map((v,i)=>v+dt*k1[i]/2));
        const k3=deriv(time+dt/2,state.map((v,i)=>v+dt*k2[i]/2));
        const k4=deriv(time+dt,state.map((v,i)=>v+dt*k3[i]));
        next=state.map((v,i)=>v+dt*(k1[i]+2*k2[i]+2*k3[i]+k4[i])/6);
      }
    } catch (e) { stopped=true; reason=e.message; break; }
    if(next.some(v=>!Number.isFinite(v)||Math.abs(v)>MAX_STATE)){
      stopped=true;reason='Solution diverged or exceeded numerical limits.';break;
    }
    state=next;time+=dt;
    points.push({t:time,values:state.slice()});
  }
  if(time<tMax-1e-10 && !stopped) { stopped=true;reason='Step limit reached: increase h or reduce time span.'; }
  return {points,stopped,reason};
}

/** Binary-search interpolation through the cached RK4/Euler path. */
export function systemAtTime(points, time){
  if(!points?.length)return null;
  if(time<=points[0].t)return points[0].values.slice();
  if(time>=points.at(-1).t)return points.at(-1).values.slice();
  let lo=0,hi=points.length-1;
  while(hi-lo>1){const m=(lo+hi)>>1;if(points[m].t<time)lo=m;else hi=m;}
  const a=points[lo],b=points[hi],u=(time-a.t)/(b.t-a.t);
  return a.values.map((v,i)=>v*(1-u)+b.values[i]*u);
}

/** Parse semicolon/newline-delimited initial values: one state per line. */
export function parseInitialStates(text, dimensions, maxTrails=10){
  const rows=text.trim().split(/[;\n]+/).map(x=>x.trim()).filter(Boolean);
  if(!rows.length)throw new SyntaxError('Enter initial values, e.g. 1, 0 or 1, 0; 0, 1.');
  if(rows.length>maxTrails)throw new RangeError(`At most ${maxTrails} initial conditions are supported.`);
  return rows.map((row,i)=>{
    const parts=row.split(',').map(s=>s.trim());
    if(parts.length!==dimensions||parts.some(v=>!v || !Number.isFinite(Number(v))))
      throw new SyntaxError(`Initial state ${i+1} must contain ${dimensions} finite numbers separated by commas.`);
    return parts.map(Number);
  });
}

/** ODE system inputs may be RHS only or LaTeX derivative equations. */
export function systemRhs(input, symbol, timeName='t'){
  let text=String(input).trim();
  if(!text)return '';
  if(!text.includes('='))return text;
  const split=text.indexOf('=');
  let lhs=text.slice(0,split).replace(/\s+/g,'').replace(/\\left|\\right/g,'');
  const allowed=[
    `${symbol}'`,`${symbol}′`,
    `\\dot{${symbol}}`,
    `\\frac{d${symbol}}{d${timeName}}`,
    `\\dfrac{d${symbol}}{d${timeName}}`,
  ];
  if(!allowed.includes(lhs))throw new SyntaxError(`Expected ${symbol}' or \\dot{${symbol}} on the left.`);
  return text.slice(split+1).trim();
}

/** Deterministic pseudorandom initial data for reproducible experiments. */
export function cuckerInitial(n=80,seed=23,spread=5,speed=3){
  if(!Number.isInteger(n)||n<2||n>250)throw new RangeError('2 ≤ N ≤ 250.');
  let s=seed>>>0;
  if(!s)s=0x6d2b79f5;
  const random=()=>{s^=s<<13;s^=s>>>17;s^=s<<5;return (s>>>0)/4294967296;};
  const positions=new Float64Array(3*n),velocities=new Float64Array(3*n);
  for(let i=0;i<3*n;i++){
    positions[i]=(2*random()-1)*spread;
    velocities[i]=(2*random()-1)*speed;
  }
  return {positions,velocities};
}

/** Symmetric communication kernel. Original C++ kernel or common Cucker–Smale kernel. */
export function communicationWeight(r, kernel='algebraic', beta=0.5){
  if(kernel==='algebraic')return 1/Math.pow(1+r*r,beta);
  if(kernel==='original') {
    // C++: 1/(r + pow(r,r)); at r=0 the pow(0,0) convention is 1.
    const denominator=r+Math.pow(r,r);
    return denominator===Infinity?0:1/denominator;
  }
  throw new RangeError('Unknown communication kernel.');
}

/** Cucker–Smale RHS, pairwise symmetric to preserve total momentum. */
export function cuckerDerivative(positions,velocities,n,lambda,kernel='algebraic',beta=0.5){
  const a=new Float64Array(3*n), inv=lambda/n;
  for(let i=0;i<n;i++)for(let j=i+1;j<n;j++){
    const ii=3*i,jj=3*j;
    const dx=positions[ii]-positions[jj],dy=positions[ii+1]-positions[jj+1],dz=positions[ii+2]-positions[jj+2];
    const w=inv*communicationWeight(Math.hypot(dx,dy,dz),kernel,beta);
    for(let k=0;k<3;k++){
      const dv=w*(velocities[jj+k]-velocities[ii+k]);
      a[ii+k]+=dv;a[jj+k]-=dv;
    }
  }
  return a;
}

/** Full RK4 stage for coupled positions and velocities (not a frozen-acceleration approximation). */
export function cuckerStep(current,n,{h=0.02,lambda=4,kernel='algebraic',beta=0.5,method='rk4'}={}){
  if(!(h>0) || !Number.isFinite(h) || !Number.isFinite(lambda) || lambda<0)throw new RangeError('Provide h > 0 and λ ≥ 0.');
  const len=n*3;
  if(current.positions.length!==len||current.velocities.length!==len)throw new RangeError('Invalid agent state.');
  const p=current.positions,v=current.velocities;
  const d=(pos,vel)=>cuckerDerivative(pos,vel,n,lambda,kernel,beta);
  const advance=(original,slope,factor)=>{
    const result=new Float64Array(len);
    for(let i=0;i<len;i++)result[i]=original[i]+factor*slope[i];
    return result;
  };
  const a1=d(p,v),p1=v;
  let nextP,nextV;
  if(method==='euler'){
    nextP=advance(p,p1,h);nextV=advance(v,a1,h);
  }else if(method==='rk4'){
    const p2=advance(p,p1,h/2),v2=advance(v,a1,h/2),a2=d(p2,v2);
    const p3=advance(p,v2,h/2),v3=advance(v,a2,h/2),a3=d(p3,v3);
    const p4=advance(p,v3,h),v4=advance(v,a3,h),a4=d(p4,v4);
    nextP=new Float64Array(len);nextV=new Float64Array(len);
    for(let i=0;i<len;i++){
      nextP[i]=p[i]+h*(p1[i]+2*v2[i]+2*v3[i]+v4[i])/6;
      nextV[i]=v[i]+h*(a1[i]+2*a2[i]+2*a3[i]+a4[i])/6;
    }
  }else throw new RangeError('Select RK4 or Euler.');
  for(let i=0;i<len;i++)if(!Number.isFinite(nextP[i])||!Number.isFinite(nextV[i])||Math.abs(nextP[i])>MAX_STATE||Math.abs(nextV[i])>MAX_STATE)throw new RangeError('Particle simulation diverged.');
  return {positions:nextP,velocities:nextV};
}

export function cuckerDiagnostics(state,n){
  const mean=[0,0,0],center=[0,0,0],v=state.velocities,p=state.positions;
  for(let i=0;i<3*n;i++){center[i%3]+=p[i]/n;mean[i%3]+=v[i]/n;}
  let dispersion=0,maxGap=0;
  for(let i=0;i<n;i++){
    const k=3*i;
    dispersion+=((v[k]-mean[0])**2+(v[k+1]-mean[1])**2+(v[k+2]-mean[2])**2)/n;
    for(let j=i+1;j<n;j++){
      const l=3*j;maxGap=Math.max(maxGap,Math.hypot(v[k]-v[l],v[k+1]-v[l+1],v[k+2]-v[l+2]));
    }
  }
  return {mean,center,dispersion:Math.sqrt(dispersion),maxGap};
}
