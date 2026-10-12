import {compileLatex} from './latex.mjs';
import {integrateSystem,systemRhs} from './dynamics_math.mjs';
import {MAX_TIME} from './time-range.mjs';

export function solveLab(input){
  const {h,method}=input;
  const tMax=input.kind==='scalar'?MAX_TIME:input.tMax;
  const options={h,method,tMax,maxSteps:Math.ceil(tMax/h)+1,maxPoints:20000};
  if(input.kind==='system'){
    const fs=input.expressions.map((s,i)=>compileLatex(systemRhs(s,['x','y','z'][i]),['t','x','y','z']));
    return {results:input.initial.map(y=>integrateSystem((t,v)=>fs.map(f=>f(t,v[0],v[1],v[2]??0)),y,options))};
  }
  const {order,x0,y0,v0,expression}=input;
  const fn=compileLatex(expression,order===2?['x','y','v']:['x','y']);
  const rhs=(t,v)=>order===2?[v[1],fn(x0+t,v[0],v[1])]:[fn(x0+t,v[0]),0];
  const solve=method=>{
    const result=integrateSystem(rhs,[y0,order===2?v0:0],{...options,method,maxState:1e7});
    return {...result,steps:Math.round(result.points.at(-1).t/h),points:result.points.map(p=>({x:x0+p.t,y:p.values[0],...(order===2?{v:p.values[1]}:{})}))};
  };
  return {solution:solve(method),comparison:input.compare?solve(method==='rk4'?'euler':'rk4'):null};
}
