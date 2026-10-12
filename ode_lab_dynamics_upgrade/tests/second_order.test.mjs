import test from 'node:test';
import assert from 'node:assert/strict';
import { solveSecondOrder, nextStepSize, stepToFraction, fractionToStep } from '../assets/euler-method/math.mjs';
import { compileLatex } from '../assets/euler-method/latex.mjs';

const approx = (a,b,tol=1e-7) => assert.ok(Math.abs(a-b)<tol,`${a} != ${b} (tol ${tol})`);

test('undamped oscillator y"=-y: RK4 tracks cosine and velocity sine',()=>{
 const f=compileLatex(String.raw`y''=-y`,['x','y','v']);
 const sol=solveSecondOrder(f,0,1,0,0.05,Math.PI/2,'rk4');
 const p=sol.points.at(-1);
 approx(p.y, Math.cos(p.x), 1e-6);
 approx(p.v, -Math.sin(p.x), 1e-6);
});
test('damped oscillator y"=-y-.2y\' RK4 tracks analytic solution',()=>{
 const f=compileLatex(String.raw`y''=-y-0.2y'`,['x','y','v']);
 const sol=solveSecondOrder(f,0,1,0,0.02,10,'rk4');
 const p=sol.points.at(-1); const omega=Math.sqrt(0.99);
 const exact=Math.exp(-0.1*p.x)*(Math.cos(omega*p.x)+0.1/omega*Math.sin(omega*p.x));
 approx(p.y,exact,3e-6);
});
test('Euler still works on second order as a coupled system',()=>{
 const sol=solveSecondOrder((x,y,v)=>-y,0,1,0,0.1,0.1,'euler');
 assert.deepEqual(sol.points,[{x:0,y:1,v:0},{x:0.1,y:1,v:-0.1}]);
});
test('second-order RK4 does not use prematurely updated v',()=>{
 const sol=solveSecondOrder((x,y,v)=>-y,0,1,0,0.1,0.1,'rk4');
 const point=sol.points.at(-1);
 approx(point.y,Math.cos(.1),1e-7);
 approx(point.v,-Math.sin(.1),1e-7);
});
test('full second-order differential fraction and y prime parse as v',()=>{
 const f=compileLatex(String.raw`\frac{d^2y}{dx^2}=-y-0.2\frac{dy}{dx}`,['x','y','v']);
 approx(f(0,2,3),-2.6);
 const g=compileLatex(String.raw`y'' = - y - 0.2 y'`,['x','y','v']);
 approx(g(0,2,3),-2.6);
});
test('invalid first-order y prime reference remains invalid',()=>{
 assert.throws(()=>compileLatex(String.raw`y'= y'`,['x','y']));
});
test('step slider log mapping is round trip and supports drag positions',()=>{
 for (const h of [.001,.01,.1,.5,1,2]) approx(fractionToStep(stepToFraction(h)),h,1e-8);
 assert.ok(fractionToStep(.8)>fractionToStep(.2));
 assert.equal(nextStepSize(.1,1.25),.125);
});
test('invalid h and solution blow-up are safe',()=>{
 assert.throws(()=>solveSecondOrder(()=>-1,0,0,0,0,1,'rk4'));
 const result=solveSecondOrder((x,y,v)=>1e15,0,0,0,.1,2,'rk4');
 assert.equal(result.stopped,true);
});
