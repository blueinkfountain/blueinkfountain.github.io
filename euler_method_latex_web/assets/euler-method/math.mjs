/** Mathematical core of the browser port. No browser or third-party dependencies. */

export const EQUATIONS = Object.freeze([
  { id: 1, label: 'y²(y² − 4)', formula: 'y²(y² − 4)', latex: String.raw`y^2(y^2-4)` },
  { id: 2, label: 'y(1 − y)', formula: 'y(1 − y)', latex: String.raw`y(1-y)` },
  { id: 3, label: 'y(2 − y)', formula: 'y(2 − y)', latex: String.raw`y(2-y)` },
  { id: 4, label: 'y(1 − 2y)', formula: 'y(1 − 2y)', latex: String.raw`y(1-2y)` },
  { id: 5, label: '−y²', formula: '−y²', latex: String.raw`-y^2` },
  { id: 6, label: 'y/(1 + x²)', formula: 'y/(1 + x²)', latex: String.raw`\frac{y}{1+x^2}` },
  { id: 7, label: 'exp(sin x)', formula: 'exp(sin x)', latex: String.raw`\exp(\sin(x))` },
  { id: 8, label: 'exp(−y²)', formula: 'exp(−y²)', latex: String.raw`\exp(-y^2)` },
]);

export function derivative(index, x, y) {
  switch (Number(index)) {
    case 1: return y * y * (y * y - 4);
    case 2: return y * (1 - y);
    case 3: return y * (2 - y);
    case 4: return y * (1 - 2 * y);
    case 5: return -y * y;
    case 6: return y / (1 + x * x);
    case 7: return Math.exp(Math.sin(x));
    case 8: return Math.exp(-y * y);
    default: throw new RangeError('Unknown differential equation: ' + index);
  }
}

const MAX_MAGNITUDE = 1e7;

/** Solve forward from (x0,y0) up to xMax (inclusive where a step fits). */
export function eulerSolve(f, x0, y0, h, xMax, maxSteps = 18000) {
  if (!(h > 0 && Number.isFinite(h))) throw new RangeError('Step size must be positive and finite.');
  if (![x0, y0, xMax].every(Number.isFinite)) throw new RangeError('Inputs must be finite.');
  const points = [{ x: x0, y: y0 }];
  const count = Math.min(maxSteps, Math.max(0, Math.floor((xMax - x0) / h + 1e-9)));
  let y = y0;
  let stopped = false;
  for (let i = 0; i < count; ++i) {
    const x = x0 + i * h;
    const dy = f(x, y);
    const next = y + h * dy;
    if (!Number.isFinite(next) || Math.abs(next) > MAX_MAGNITUDE) {
      stopped = true;
      break;
    }
    y = next;
    points.push({ x: x0 + (i + 1) * h, y });
  }
  if (count >= maxSteps && x0 + count * h < xMax - h) stopped = true;
  return { points, stopped };
}

export function rk4Solve(f, x0, y0, h, xMax, maxSteps = 45000) {
  if (!(h > 0 && Number.isFinite(h))) throw new RangeError('Step size must be positive and finite.');
  if (![x0, y0, xMax].every(Number.isFinite)) throw new RangeError('Inputs must be finite.');
  const points = [{ x: x0, y: y0 }];
  const count = Math.min(maxSteps, Math.max(0, Math.floor((xMax - x0) / h + 1e-9)));
  let y = y0;
  let stopped = false;
  for (let i = 0; i < count; ++i) {
    const x = x0 + i * h;
    const k1 = f(x, y);
    const k2 = f(x + h / 2, y + h * k1 / 2);
    const k3 = f(x + h / 2, y + h * k2 / 2);
    const k4 = f(x + h, y + h * k3);
    const next = y + h * (k1 + 2 * k2 + 2 * k3 + k4) / 6;
    if (!Number.isFinite(next) || Math.abs(next) > MAX_MAGNITUDE) {
      stopped = true;
      break;
    }
    y = next;
    points.push({ x: x0 + (i + 1) * h, y });
  }
  if (count >= maxSteps && x0 + count * h < xMax - h) stopped = true;
  return { points, stopped };
}

/**
 * In the original C++ 1/2, 1/3 and 1/12 are INTEGER division and evaluate to 0.
 * 'compiled' reflects what the user's original C++ actually plotted.
 * 'fractions' reflects the likely mathematical intention instead.
 */
export function parameterPoint(t, mode = 'compiled') {
  if (mode === 'compiled') {
    return {
      x: Math.sin(4 * t) * (Math.E - 2 * Math.cos(18 * t)),
      y: Math.cos(5 * t) * (Math.E - 2 * Math.cos(11 * t)),
    };
  }
  if (mode === 'fractions') {
    const correction = Math.sin(1 / 12) ** 5;
    return {
      x: Math.sin(4 * t) * (Math.exp(Math.cos(t / 2)) - 2 * Math.cos(18 * t) - correction),
      y: Math.cos(5 * t) * (Math.exp(Math.cos(t / 3)) - 2 * Math.cos(11 * t) - correction),
    };
  }
  throw new RangeError('Unknown parameter mode: ' + mode);
}

export function nearestParameterTime(x, y, mode = 'compiled', start = 0, end = 100, step = 0.01) {
  if (step <= 0) throw new RangeError('Step must be positive.');
  let bestT = start;
  let bestDist = Infinity;
  const n = Math.floor((end - start) / step + 1e-9);
  for (let i = 0; i <= n; ++i) {
    const t = start + i * step;
    const p = parameterPoint(t, mode);
    const squared = (p.x - x) ** 2 + (p.y - y) ** 2;
    if (squared < bestDist) {
      bestDist = squared;
      bestT = t;
    }
  }
  return { t: bestT, distance: Math.sqrt(bestDist) };
}

/** Compare at the last Euler x by linearly interpolating the fine RK4 path. */
export function estimateDifference(eulerPoints, rk4Points) {
  if (!eulerPoints.length || !rk4Points.length) return NaN;
  const p = eulerPoints.at(-1);
  if (rk4Points.length === eulerPoints.length && rk4Points === eulerPoints) return 0;
  let lo = 0, hi = rk4Points.length - 1;
  if (p.x < rk4Points[lo].x || p.x > rk4Points[hi].x + 1e-9) return NaN;
  while (lo + 1 < hi) {
    const mid = Math.floor((lo + hi) / 2);
    if (rk4Points[mid].x < p.x) lo = mid;
    else hi = mid;
  }
  const a = rk4Points[lo], b = rk4Points[hi];
  const weight = b.x === a.x ? 0 : Math.max(0, Math.min(1, (p.x - a.x) / (b.x - a.x)));
  return Math.abs(p.y - (a.y * (1 - weight) + b.y * weight));
}
