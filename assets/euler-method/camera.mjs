/** Translate screen-space motion into the graph's world-space camera offset. */
export function panByPixels(pan, dx, dy, scale) {
  return [pan[0] - dx / scale, pan[1] + dy / scale];
}
export function dragRotates(mode, in3d, shiftKey) {
  return in3d && (mode === 'cucker' ? shiftKey : !shiftKey);
}
export function arrowMovement(key) {
  return ({ArrowLeft: [-30, 0], ArrowRight: [30, 0], ArrowUp: [0, -30], ArrowDown: [0, 30]})[key] ?? null;
}
