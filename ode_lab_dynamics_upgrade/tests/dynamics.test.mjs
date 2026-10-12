import test from 'node:test';
import assert from 'node:assert/strict';
import {compileLatex} from '../assets/euler-method/latex.mjs';
import {
  integrateSystem, systemAtTime, systemRhs, parseInitialStates,
  cuckerInitial, cuckerStep, cuckerDiagnostics, communicationWeight,
} from '../assets/euler-method/dynamics_math.mjs';

const close=(a,b,eps=1e-5)=>assert.ok(Math.abs(a-b)<eps,`Expected ${a} ≈ ${b}`);
test('2D oscillator RK4 accurately closes a full period',()=>{
 const r=integrateSystem((t,[x,y])=>[y,-x],[1,0],{tMax:2*Math.PI,h:.01});
 assert.equal(r.stopped,false);
 close(r.points.at(-1).values[0],1,1e-7);
 close(r.points.at(-1).values[1],0,1e-7);
});
test('3D constant velocity RK4 advances every component and can interpolate time',()=>{
 const r=integrateSystem(()=>[1,2,-3],[2,1,-4],{tMax:3,h:.1});
 assert.deepEqual(r.points.at(-1).values.map(v=>Math.round(v)),[5,7,-13]);
 const at=systemAtTime(r.points,1.5);close(at[0],3.5);close(at[1],4);close(at[2],-8.5);
});
test('Euler and RK4 are distinct and use the intended vector method',()=>{
 const f=(t,v)=>[v[0],v[1]];
 const rk=integrateSystem(f,[1,1],{h:.5,tMax:1,method:'rk4'});
 const e=integrateSystem(f,[1,1],{h:.5,tMax:1,method:'euler'});
 assert.ok(Math.abs(rk.points.at(-1).values[0]-Math.E)<.002);
 close(e.points.at(-1).values[0],2.25);
});
test('integration validates dimensions, steps, stop limits, and divergence',()=>{
 assert.throws(()=>integrateSystem(()=>[1],[1,0],{h:0}),/h > 0/);
 const limited=integrateSystem(()=>[1,1],[0,0],{h:.01,tMax:5,maxSteps:4});
 assert.equal(limited.stopped,true);
 assert.match(limited.reason,/limit/);
 const diverged=integrateSystem(()=>[Infinity,1],[0,0],{h:.01,tMax:5});
 assert.equal(diverged.stopped,true);
});
test('safe LaTeX parsing supports z, t, derivative LHS, and vector fields',()=>{
 const fx=compileLatex(systemRhs(String.raw`\dot{x}=10(y-x)`,'x'),['t','x','y','z']);
 const fz=compileLatex(systemRhs(String.raw`\frac{dz}{dt}=xy-\frac{8}{3}z`,'z'),['t','x','y','z']);
 close(fx(0,1,2,3),10);
 close(fz(0,1,2,3),-6);
 assert.throws(()=>systemRhs("y'=x",'x'),/Expected/);
 assert.throws(()=>compileLatex('\\foo',['x']),/Unsupported/);
});
test('multiple initial conditions are parsed and validated',()=>{
 assert.deepEqual(parseInitialStates('1, 0; 2, 3',2),[[1,0],[2,3]]);
 assert.deepEqual(parseInitialStates('1,2,3\n4,5,6',3),[[1,2,3],[4,5,6]]);
 assert.throws(()=>parseInitialStates('1,2,3',2),/2 finite/);
 assert.throws(()=>parseInitialStates('1,abc',2),/2 finite/);
});
test('Cucker initial conditions are deterministic and bounded by N',()=>{
 const a=cuckerInitial(15,22),b=cuckerInitial(15,22);
 assert.deepEqual([...a.positions],[...b.positions]);
 assert.throws(()=>cuckerInitial(251),/250/);
});
test('Cucker RK4 preserves uniform velocities and translates uniformly',()=>{
 const start=cuckerInitial(12,22);start.velocities.fill(0);
 for(let i=0;i<12;i++)start.velocities[3*i]=2;
 const next=cuckerStep(start,12,{h:.1,lambda:6});
 for(let i=0;i<12;i++){
  close(next.positions[3*i]-start.positions[3*i],.2,1e-12);
  close(next.velocities[3*i],2,1e-12);
 }
});
test('Cucker total momentum is preserved with both RK4 and Euler',()=>{
 const first=cuckerInitial(20,83);
 for(const method of ['rk4','euler']){
  let current=first;
  const before=cuckerDiagnostics(current,20).mean;
  for(let i=0;i<10;i++)current=cuckerStep(current,20,{h:.025,lambda:3,method});
  const after=cuckerDiagnostics(current,20).mean;
  for(let k=0;k<3;k++)close(after[k],before[k],1e-10);
 }
});
test('Cucker velocity diameter decreases for two particles with common kernel',()=>{
 const a={positions:new Float64Array([0,0,0,1,0,0]),velocities:new Float64Array([2,0,0,-2,0,0])};
 const before=cuckerDiagnostics(a,2).maxGap;
 const b=cuckerStep(a,2,{h:.05,lambda:5});
 assert.ok(cuckerDiagnostics(b,2).maxGap<before);
});
test('original communication kernel matches the C++ expression',()=>{
 for(const r of [0,.1,1,2])close(communicationWeight(r,'original'),1/(r+Math.pow(r,r)),1e-12);
});
