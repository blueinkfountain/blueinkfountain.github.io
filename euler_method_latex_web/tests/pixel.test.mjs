import test from 'node:test';
import assert from 'node:assert/strict';
import {clipSegment, rasterLine} from '../assets/euler-method/pixel.mjs';

test('clipSegment rejects lines entirely outside the canvas', () => {
  assert.equal(clipSegment(-100,-100,-50,-50,0,0,100,100), null);
  assert.equal(clipSegment(-100,20,-20,20,0,0,100,100), null);
});

test('clipSegment clips crossing lines to the viewport', () => {
  const p=clipSegment(-20,10,120,10,0,0,100,100);
  assert.ok(p);
  assert.deepEqual(p.map(x=>Math.round(x)),[0,10,100,10]);
});

test('rasterLine creates thin, connected integer pixel stair-steps',()=>{
  const pts=[];
  rasterLine(0,0,9,4,(x,y)=>pts.push([x,y]));
  assert.deepEqual(pts.at(0),[0,0]);
  assert.deepEqual(pts.at(-1),[9,4]);
  assert.equal(pts.length,10);
  for(let i=1;i<pts.length;i++) {
    assert.ok(Math.abs(pts[i][0]-pts[i-1][0])<=1);
    assert.ok(Math.abs(pts[i][1]-pts[i-1][1])<=1);
  }
});

test('rasterLine has no antialiasing or arbitrary coordinate noise',()=>{
  const pts=[];
  rasterLine(2.3,1.8,5.7,7.2,(x,y)=>pts.push([x,y]));
  assert.ok(pts.length);
  assert.ok(pts.every(([x,y])=>Number.isInteger(x)&&Number.isInteger(y)));
});
