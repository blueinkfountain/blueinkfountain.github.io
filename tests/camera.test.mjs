import test from 'node:test';
import assert from 'node:assert/strict';
import {panByPixels, dragRotates, arrowMovement} from '../assets/euler-method/camera.mjs';

test('dragging translates the graph by the same screen distance at any zoom',()=>{
  assert.deepEqual(panByPixels([2,3],60,-30,30),[0,2]);
  assert.deepEqual(panByPixels([2,3],60,-30,60),[1,2.5]);
});
test('Cucker dragging pans by default, Shift rotates only a 3D view',()=>{
  assert.equal(dragRotates('cucker',true,false),false);
  assert.equal(dragRotates('cucker',true,true),true);
  assert.equal(dragRotates('cucker',false,true),false);
  assert.equal(dragRotates('system',true,false),false);
  assert.equal(dragRotates('system',true,true),true);
  assert.equal(dragRotates('system',false,true),false);
});
test('arrow keys move the graph in four directions and ignore other keys',()=>{
  assert.deepEqual(arrowMovement('ArrowLeft'),[-30,0]);
  assert.deepEqual(arrowMovement('ArrowRight'),[30,0]);
  assert.deepEqual(arrowMovement('ArrowUp'),[0,-30]);
  assert.deepEqual(arrowMovement('ArrowDown'),[0,30]);
  assert.equal(arrowMovement('a'),null);
});
