import assert from 'node:assert';
import { clampPercent } from './compare_math.js';
import { readFileSync } from 'node:fs';

// Test clampPercent
// Inside
assert.strictEqual(clampPercent(50, 0, 100), 50);
assert.strictEqual(clampPercent(25, 0, 100), 25);
assert.strictEqual(clampPercent(75, 0, 100), 75);

// Outside
assert.strictEqual(clampPercent(-10, 0, 100), 0);
assert.strictEqual(clampPercent(110, 0, 100), 100);

// Zero width
assert.strictEqual(clampPercent(50, 0, 0), 50);
assert.strictEqual(clampPercent(0, 0, 0), 50);
assert.strictEqual(clampPercent(100, 0, 0), 50);

// Negative width
assert.strictEqual(clampPercent(50, 0, -10), 50);

// With offset
assert.strictEqual(clampPercent(50, 25, 100), 25);
assert.strictEqual(clampPercent(75, 25, 100), 50);
assert.strictEqual(clampPercent(125, 25, 100), 100);
assert.strictEqual(clampPercent(25, 25, 100), 0);

// Check compare.js content
const compareJs = readFileSync('./compare.js', 'utf8');
assert.ok(compareJs.includes('export function Compare'), 'Should export Compare');
assert.ok(compareJs.includes('export { clampPercent }'), 'Should re-export clampPercent');
assert.ok(compareJs.includes('setPointerCapture'), 'Should use setPointerCapture');
assert.ok(compareJs.includes('role="slider"'), 'Should have role="slider"');
assert.ok(compareJs.includes('ArrowLeft'), 'Should handle ArrowLeft');
assert.ok(compareJs.includes('aria-valuenow'), 'Should have aria-valuenow');

console.log('ok');
