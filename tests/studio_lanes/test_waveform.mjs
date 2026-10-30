import assert from "node:assert";
import { peaks, timeToX, xToTime } from "./waveform_math.js";
import { readFileSync } from "node:fs";

// Test peaks
const samples = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8];
const p = peaks(samples, 4);
assert.strictEqual(p.length, 4);
assert.ok(Math.abs(p[0] - 0.25) < 1e-6, `p[0] should be 0.25, got ${p[0]}`);
assert.ok(Math.abs(p[1] - 0.5) < 1e-6, `p[1] should be 0.5, got ${p[1]}`);
assert.ok(Math.abs(p[2] - 0.75) < 1e-6, `p[2] should be 0.75, got ${p[2]}`);
assert.ok(Math.abs(p[3] - 1.0) < 1e-6, `p[3] should be 1.0, got ${p[3]}`);

// Test empty input
const emptyP = peaks([], 4);
assert.strictEqual(emptyP.length, 4);
assert.ok(emptyP.every(v => v === 0));

// Test timeToX
assert.strictEqual(timeToX(1, 10, 100), 10);
assert.strictEqual(timeToX(5, 10, 100), 50);
assert.strictEqual(timeToX(0, 10, 100), 0);

// Test xToTime
assert.strictEqual(xToTime(10, 10, 100), 1);
assert.strictEqual(xToTime(50, 10, 100), 5);
assert.strictEqual(xToTime(150, 10, 100), 10); // clamped
assert.strictEqual(xToTime(-10, 10, 100), 0); // clamped

// Check waveform.js content
const code = readFileSync("./waveform.js", "utf8");
assert.ok(code.includes("export function Waveform"));
assert.ok(code.includes("decodeAudioData"));
assert.ok(code.includes("ResizeObserver"));

console.log("ok");
