import test from 'node:test';
import assert from 'node:assert/strict';
import {pointAtElapsedTime, solveSecondOrder, solveNumerically} from '../assets/euler-method/math.mjs';

const approx=(a,b,tol=1e-10)=>assert.ok(Math.abs(a-b)<=tol,`${a} != ${b}`);

test('timeline interpolates first-order numerical states without recomputing',()=>{
  const result=solveNumerically(()=>1,2,3,0.5,3.5,'rk4');
  const p=pointAtElapsedTime(result.points,0.75);
  approx(p.x,2.75);
  approx(p.y,3.75);
  approx(pointAtElapsedTime(result.points,0).y,3);
  approx(pointAtElapsedTime(result.points,100).x,3.5);
});
test('timeline interpolates both y and v for second-order phase mode',()=>{
  const result=solveSecondOrder(()=>-1,0,1,0,1,2,'euler');
  const p=pointAtElapsedTime(result.points,.5);
  approx(p.x,.5);
  approx(p.y,1);
  approx(p.v,-.5);
});
test('timeline handles invalid data and degenerate paths',()=>{
  assert.equal(pointAtElapsedTime([],1),null);
  assert.equal(pointAtElapsedTime([{x:0,y:5}],Infinity),null);
  assert.deepEqual(pointAtElapsedTime([{x:0,y:5}],5),{x:0,y:5});
});
