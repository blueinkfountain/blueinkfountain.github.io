import test from 'node:test';
import assert from 'node:assert/strict';
import {compileLatex} from '../assets/euler-method/latex.mjs';
import {EQUATIONS,derivative,eulerSolve} from '../assets/euler-method/math.mjs';

const f=(latex,x,y)=>compileLatex(latex,['x','y'])(x,y);
const g=(latex,t)=>compileLatex(latex,['t'])(t);

test('all 8 original ODE preset formulas match C++ numerical definitions',()=>{
 for(const p of EQUATIONS) {
   for(const [x,y] of [[1,.5],[2,1.3],[.3,-.2]]) {
     assert.ok(Math.abs(f(p.latex,x,y)-derivative(p.id,x,y))<1e-11,p.latex);
   }
 }
});
test('original green parametric x(t), y(t) evaluate correctly',()=>{
 const px=g(String.raw`\sin(4t)(e-2\cos(18t))`,.7);
 const py=g(String.raw`\cos(5t)(e-2\cos(11t))`,.7);
 assert.ok(Math.abs(px-Math.sin(2.8)*(Math.E-2*Math.cos(12.6)))<1e-12);
 assert.ok(Math.abs(py-Math.cos(3.5)*(Math.E-2*Math.cos(7.7)))<1e-12);
});
test('LaTeX fractions, radicals, powers, implicit multiplication',()=>{
 assert.equal(f(String.raw`\frac{y}{1+x^2}`,2,5),1);
 assert.equal(f(String.raw`3x^2+2y(1-y)`,2,.5),12.5);
 assert.equal(g(String.raw`\sqrt{t^2+9}`,4),5);
 assert.ok(Math.abs(g(String.raw`\sqrt[3]{t}`,27)-3)<1e-12);
 assert.equal(g(String.raw`\frac{t}{2}`,4),2);
});
test('common LaTeX commands and \\left / \\right work',()=>{
 assert.ok(Math.abs(g(String.raw`\sin^2(t)+\cos^2(t)`,1.2)-1)<1e-12);
 assert.ok(Math.abs(g(String.raw`\left|\sin(t)\right|`,-1)-Math.abs(Math.sin(-1)))<1e-12);
 assert.ok(Math.abs(g(String.raw`\ln(e^t)`,2)-2)<1e-12);
 assert.ok(Math.abs(g(String.raw`\exp(-t^2)`,.5)-Math.exp(-.25))<1e-12);
});
test('variables and optional differential equation LHS',()=>{
 assert.equal(f(String.raw`\frac{dy}{dx}=y(1-y)`,0,.5),.25);
 assert.equal(g(String.raw`x(t)=\sin(t)`,Math.PI/2),1);
 assert.equal(g(String.raw`y(t)=\cos(t)`,0),1);
 assert.equal(f('f(x,y)=x+y',2,5),7);
 assert.equal(f("y'=x+1",3,1),4);
});
test('Euler recomputes with a new typed formula',()=>{
 const a=eulerSolve(compileLatex('y',['x','y']),0,1,.1,.2).points;
 const b=eulerSolve(compileLatex('2y',['x','y']),0,1,.1,.2).points;
 assert.equal(a[1].y,1.1);
 assert.equal(b[1].y,1.2);
});
test('negative powers and precedence',()=>{
 assert.equal(g('-t^2',3),-9);
 assert.equal(g('t^-2',2),.25);
 assert.equal(g('2^3^2',0),512);
});
test('malformed and unsupported input is rejected',()=>{
 for(const bad of ['', 'y+',String.raw`\foo(x)`,'window.alert(1)', 'x+y', 'y)(',String.raw`\frac{1}`]){
  assert.throws(()=>compileLatex(bad,['t']),/./,bad);
 }
 assert.throws(()=>compileLatex('t',['x','y']),/variable/);
 assert.throws(()=>compileLatex('a',['x','y']),/symbol/);
});
test('arithmetic does not run JavaScript',()=>{
 assert.throws(()=>compileLatex('constructor.constructor', ['x','y']),/./);
 assert.throws(()=>compileLatex('x;alert(1)', ['x','y']),/./);
});
test('formulas are constrained by length and complexity',()=>{
 assert.throws(()=>compileLatex('x+'.repeat(160)+'1',['x','y']),/300/);
 assert.throws(()=>compileLatex('('.repeat(70)+'x'+')'.repeat(70),['x','y']),/deeply/);
});
