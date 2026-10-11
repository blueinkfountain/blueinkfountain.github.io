import test from 'node:test';
import assert from 'node:assert/strict';
import {
  EQUATIONS, derivative, eulerSolve, rk4Solve,
  parameterPoint, nearestParameterTime, estimateDifference,
} from '../assets/euler-method/math.mjs';

test('eight vector-field choices preserve the original C++ definitions', () => {
  assert.equal(EQUATIONS.length, 8);
  assert.equal(derivative(1, 0, 3), 45);
  assert.equal(derivative(2, 0, 0.5), 0.25);
  assert.equal(derivative(3, 5, 0.5), 0.75);
  assert.equal(derivative(4, 5, 0.5), 0);
  assert.equal(derivative(5, 5, 0.5), -0.25);
  assert.equal(derivative(6, 1, 2), 1);
  assert.equal(derivative(7, 0, 99), 1);
  assert.equal(derivative(8, 2, 0), 1);
});

test('explicit Euler handles y’=y(1-y) from an initial condition', () => {
  const p = eulerSolve((x, y) => y * (1 - y), 0, 0.5, 0.1, 0.3);
  assert.equal(p.points.length, 4);
  assert.ok(Math.abs(p.points[1].y - 0.525) < 1e-12);
  assert.ok(Math.abs(p.points[2].y - 0.5499375) < 1e-10);
  assert.ok(Math.abs(p.points[3].x - 0.3) < 1e-12);
});

test('Euler preserves initial point and rejects invalid h', () => {
  assert.deepEqual(eulerSolve((x,y) => y, 2, 4, 0.1, 2).points, [{x:2,y:4}]);
  assert.throws(() => eulerSolve((x,y) => y, 0, 1, 0, 2), /positive/);
  assert.throws(() => eulerSolve((x,y) => y, 0, 1, -1, 2), /positive/);
});

test('Euler returns a bounded partial curve for blow-up', () => {
  const result = eulerSolve((x,y)=>y*y, 0, 2, 0.2, 10);
  assert.equal(result.stopped, true);
  assert.ok(result.points.length < 20000);
  for (const p of result.points) assert.ok(Number.isFinite(p.y));
});

test('RK4 comparison is significantly more accurate than Euler for y’=y', () => {
  const e = eulerSolve((x,y) => y, 0, 1, 0.1, 1).points.at(-1).y;
  const r = rk4Solve((x,y) => y, 0, 1, 0.1, 1).points.at(-1).y;
  assert.ok(Math.abs(r - Math.E) < Math.abs(e - Math.E) / 100);
});

test('original compiled C++ parameter expressions preserve integer division semantics', () => {
  const t = 0.314;
  const p = parameterPoint(t, 'compiled');
  assert.ok(Math.abs(p.x - Math.sin(4*t)*(Math.E-2*Math.cos(18*t))) < 1e-10);
  assert.ok(Math.abs(p.y - Math.cos(5*t)*(Math.E-2*Math.cos(11*t))) < 1e-10);
  const intended = parameterPoint(t, 'fractions');
  assert.ok(Math.abs(intended.x - p.x) > 0.001);
});

test('parameter curve click selection returns a nearby time', () => {
  const t = 1.23;
  const p = parameterPoint(t, 'compiled');
  const nearest = nearestParameterTime(p.x, p.y, 'compiled', 0, 2, 0.001);
  assert.ok(Math.abs(nearest.t - t) < 0.01);
  assert.ok(nearest.distance < 0.01);
});

test('comparison interpolation is finite and zero for identical trajectories', () => {
  const points = [{x:0,y:1}, {x:1,y:2}];
  assert.equal(estimateDifference(points, points), 0);
});
