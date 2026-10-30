import assert from 'node:assert';
import { pathFor, ringPush, trend } from './sparkline_math.js';
import { readFileSync } from 'node:fs';

// Test pathFor empty
const empty = pathFor([], 100, 50);
assert.strictEqual(empty.d, '');

// Test pathFor single value
const single = pathFor([5], 100, 50);
assert.ok(single.d.startsWith('M'));
assert.ok(single.d.includes('L'));
assert.strictEqual(single.last.x, 98); // w - pad
assert.strictEqual(single.last.y, 25); // h / 2

// Test pathFor flat series
const flat = pathFor([5, 5, 5], 100, 50);
assert.ok(flat.d.includes('M 2 25'));
assert.ok(flat.d.includes('L 98 25'));
assert.strictEqual(flat.last.x, 98);
assert.strictEqual(flat.last.y, 25);

// Test pathFor bounds
const bounds = pathFor([0, 10], 100, 50);
assert.strictEqual(bounds.last.x, 98);
assert.strictEqual(bounds.last.y, 2); // h - pad

// Test ringPush
let arr = [1, 2, 3];
arr = ringPush(arr, 4, 3);
assert.deepStrictEqual(arr, [2, 3, 4]);
arr = ringPush(arr, 5, 3);
assert.deepStrictEqual(arr, [3, 4, 5]);

// Test trend
assert.strictEqual(trend([1, 2, 3, 4, 5, 6]), 'up');
assert.strictEqual(trend([6, 5, 4, 3, 2, 1]), 'down');
assert.strictEqual(trend([5, 5, 5, 5, 5, 5]), 'flat');
assert.strictEqual(trend([1, 2, 3]), 'up');

// Check sparkline.js text
const sparklineCode = readFileSync('./sparkline.js', 'utf8');
assert.ok(sparklineCode.includes('export function Sparkline'));
assert.ok(sparklineCode.includes('role="img"'));
assert.ok(sparklineCode.includes('aria-label'));
assert.ok(sparklineCode.includes('var(--a2)'));

console.log('ok');
