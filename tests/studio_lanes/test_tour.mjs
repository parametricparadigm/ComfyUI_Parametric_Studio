import assert from 'node:assert';
import { createTour, start, next, back, skip, current, progress, shouldAutoStart } from './tour_logic.js';
import { readFileSync } from 'fs';

const steps = [
  { id: '1', target: '#a', title: 'T1', text: 'X1' },
  { id: '2', target: '#b', title: 'T2', text: 'X2' },
  { id: '3', target: null, title: 'T3', text: 'X3' }
];

// Test createTour
let t = createTour(steps);
assert.strictEqual(t.index, 0);
assert.strictEqual(t.done, false);
assert.strictEqual(t.steps.length, 3);

// Test start
t = start(t);
assert.strictEqual(t.index, 0);
assert.strictEqual(t.done, false);

// Test next
t = next(t);
assert.strictEqual(t.index, 1);
assert.strictEqual(t.done, false);

t = next(t);
assert.strictEqual(t.index, 2);
assert.strictEqual(t.done, false);

t = next(t);
assert.strictEqual(t.index, 2);
assert.strictEqual(t.done, true);

// Test current
assert.strictEqual(current(t), null);

t = createTour(steps);
assert.strictEqual(current(t).id, '1');

// Test back
t = createTour(steps);
t = next(t);
assert.strictEqual(t.index, 1);
t = back(t);
assert.strictEqual(t.index, 0);
t = back(t);
assert.strictEqual(t.index, 0);

// Test skip
t = createTour(steps);
t = skip(t);
assert.strictEqual(t.done, true);

// Test progress
t = createTour(steps);
let p = progress(t);
assert.strictEqual(p.index, 0);
assert.strictEqual(p.total, 3);
assert.strictEqual(p.done, false);

t = next(t);
p = progress(t);
assert.strictEqual(p.index, 1);

// Test immutability
const original = createTour(steps);
const modified = next(original);
assert.strictEqual(original.index, 0);
assert.strictEqual(modified.index, 1);
assert.notStrictEqual(original, modified);

// Test shouldAutoStart
assert.strictEqual(shouldAutoStart(null), true);
assert.strictEqual(shouldAutoStart(''), true);
assert.strictEqual(shouldAutoStart('done'), false);
assert.strictEqual(shouldAutoStart('other'), true);

// Test tour.js content
const tourJs = readFileSync('./tour.js', 'utf8');
assert(tourJs.includes('export function Tour'));
assert(tourJs.includes('getBoundingClientRect'));
assert(tourJs.includes('Escape'));
assert(tourJs.includes('role="dialog"'));

console.log('ok');
