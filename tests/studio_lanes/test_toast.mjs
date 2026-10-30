import assert from 'node:assert';
import { createToasts, pushToast, dismiss, expire } from './toast_logic.js';

// Test createToasts
let state = createToasts();
assert.deepStrictEqual(state, { items: [], nextId: 1 });

// Test pushToast basic
state = pushToast(state, { kind: 'info', text: 'Hello', ms: 4000, now: 1000 });
assert.strictEqual(state.items.length, 1);
assert.strictEqual(state.items[0].id, 1);
assert.strictEqual(state.items[0].text, 'Hello');
assert.strictEqual(state.items[0].kind, 'info');
assert.strictEqual(state.items[0].count, 1);
assert.strictEqual(state.items[0].createdAt, 1000);
assert.strictEqual(state.items[0].until, 5000);
assert.strictEqual(state.nextId, 2);

// Test pushToast second item
state = pushToast(state, { kind: 'ok', text: 'World', ms: 3000, now: 2000 });
assert.strictEqual(state.items.length, 2);
assert.strictEqual(state.items[1].id, 2);
assert.strictEqual(state.items[1].text, 'World');
assert.strictEqual(state.items[1].kind, 'ok');
assert.strictEqual(state.items[1].until, 5000);
assert.strictEqual(state.nextId, 3);

// Test duplicate merge within 1000ms
state = pushToast(state, { kind: 'info', text: 'Hello', ms: 4000, now: 1500 });
assert.strictEqual(state.items.length, 2);
assert.strictEqual(state.items[0].count, 2);
assert.strictEqual(state.items[0].id, 1);
assert.strictEqual(state.nextId, 3); // nextId should not increment on merge

// Test duplicate NOT merged if > 1000ms
state = pushToast(state, { kind: 'info', text: 'Hello', ms: 4000, now: 3000 });
assert.strictEqual(state.items.length, 3);
assert.strictEqual(state.items[2].id, 3);
assert.strictEqual(state.items[2].count, 1);
assert.strictEqual(state.nextId, 4);

// Test max 4 visible: add more to exceed cap
state = pushToast(state, { kind: 'warn', text: 'A', ms: 4000, now: 4000 });
assert.strictEqual(state.items.length, 4);
state = pushToast(state, { kind: 'error', text: 'B', ms: 4000, now: 5000 });
assert.strictEqual(state.items.length, 4);
// Oldest (id 1) should be dropped
assert.strictEqual(state.items[0].id, 2);
assert.strictEqual(state.items[3].id, 5);
assert.strictEqual(state.nextId, 6);

// Test dismiss
state = dismiss(state, 2);
assert.strictEqual(state.items.length, 3);
assert.strictEqual(state.items[0].id, 3);
assert.strictEqual(state.nextId, 6);

// Test expire
state = expire(state, 5000);
// Items with until <= 5000 should be removed
// id 3: until = 4000+4000=8000 > 5000, keep
// id 4: until = 5000+4000=9000 > 5000, keep
// id 5: until = 5000+4000=9000 > 5000, keep
assert.strictEqual(state.items.length, 3);

// Test expire removing items
state = expire(state, 9000);
// id 3: until 8000 <= 9000, remove
// id 4: until 9000 <= 9000, remove
// id 5: until 9000 <= 9000, remove
assert.strictEqual(state.items.length, 0);
assert.strictEqual(state.nextId, 6);

// Test toast.js exports and aria-live
const fs = await import('node:fs');
const toastJs = fs.readFileSync('./toast.js', 'utf8');
assert.ok(toastJs.includes('export function Toasts'), 'toast.js should export Toasts');
assert.ok(toastJs.includes('aria-live="polite"'), 'toast.js should have aria-live="polite"');
assert.ok(toastJs.includes('role="status"'), 'toast.js should have role="status"');

console.log('ok');
