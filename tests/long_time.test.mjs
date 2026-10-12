import test from 'node:test';
import assert from 'node:assert/strict';
import {integrateSystem} from '../assets/euler-method/dynamics_math.mjs';

test('long integration reaches 10000 with the requested step and bounded plot storage',()=>{
  let calls=0;
  const result=integrateSystem(()=>{calls++;return [1,0];},[0,2],{tMax:10000,h:.1,method:'euler',maxSteps:100001,maxPoints:2000});
  assert.equal(result.stopped,false);
  assert.equal(result.points.at(-1).t,10000);
  assert.ok(Math.abs(result.points.at(-1).values[0]-10000)<1e-7);
  assert.ok(calls>=100000);
  assert.ok(result.points.length<=2002);
});

import {solveLab} from '../assets/euler-method/solver.mjs';
test('scalar first and second order solutions reach elapsed time 1000',()=>{
  for(const order of [1,2]){
    const {solution}=solveLab({kind:'scalar',expression:'0',order,x0:2,y0:3,v0:0,h:.1,method:'rk4'});
    assert.equal(solution.points.at(-1).x,1002);
    assert.equal(solution.points.at(-1).y,3);
    assert.equal(solution.stopped,false);
    assert.ok(solution.points.length<=20002);
  }
});
test('system solutions reach 10000 without silently increasing h',()=>{
  const {results}=solveLab({kind:'system',expressions:['1','0'],initial:[[0,2]],tMax:10000,h:.1,method:'rk4'});
  assert.equal(results[0].points.at(-1).t,10000);
  assert.ok(Math.abs(results[0].points.at(-1).values[0]-10000)<1e-7);
  assert.equal(results[0].stopped,false);
});
