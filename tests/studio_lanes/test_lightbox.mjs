import assert from 'node:assert';
import { zoomAt, clampPan, fitScale, next } from './lightbox_math.js';
import { readFileSync } from 'fs';

// Test zoomAt
const v1 = { scale: 1, x: 0, y: 0 };
const z1 = zoomAt(v1, 2, 100, 100);
assert.strictEqual(z1.scale, 2);
assert.strictEqual(z1.x, -100);
assert.strictEqual(z1.y, -100);

// Test clampPan
const c1 = clampPan({ scale: 2, x: 100, y: 100 }, 100, 100, 200, 200);
assert.strictEqual(c1.x, 0);
assert.strictEqual(c1.y, 0);

const c2 = clampPan({ scale: 0.5, x: 100, y: 100 }, 100, 100, 200, 200);
assert.strictEqual(c2.x, 75);
assert.strictEqual(c2.y, 75);

// Test fitScale
const f1 = fitScale(100, 100, 200, 200);
assert.strictEqual(f1, 2);

const f2 = fitScale(200, 100, 200, 200);
assert.strictEqual(f2, 1);

// Test next
assert.strictEqual(next(0, 5, 1), 1);
assert.strictEqual(next(4, 5, 1), 0);
assert.strictEqual(next(0, 5, -1), 4);

// Check lightbox.js content
const code = readFileSync('./lightbox.js', 'utf8');
assert(code.includes('export function Lightbox'));
assert(code.toLowerCase().includes('wheel'));
assert(code.includes('Escape'));
assert(code.includes('aria-modal'));

console.log('ok');
