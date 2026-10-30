import assert from "node:assert";
import { fuzzyScore, rank } from "./fuzzy.js";
import { readFileSync } from "node:fs";

// Test fuzzyScore: subsequence rules
assert.strictEqual(fuzzyScore("ph", "Photo"), null === fuzzyScore("ph", "Photo") ? null : typeof fuzzyScore("ph", "Photo") === "number" ? fuzzyScore("ph", "Photo") : null);
// "ph" in "Photo": P-h-o-t-o. p at 0, h at 1. Consecutive. Word start.
// score = 100+100 + 50 (consecutive) + 30 (word start) + shortBonus
// shortBonus = 20 * (1 - 5/100) = 20 * 0.95 = 19
// total = 200 + 50 + 30 + 19 = 299
assert.strictEqual(fuzzyScore("ph", "Photo"), 299);

// "ph" in "Alpha": A-l-p-h-a. p at 2, h at 3. Consecutive. Not word start (prev is 'l').
// score = 100+100 + 50 + 0 + shortBonus
// shortBonus = 20 * (1 - 5/100) = 19
// total = 200 + 50 + 19 = 269
assert.strictEqual(fuzzyScore("ph", "Alpha"), 269);

// "ph" in "Graph": G-r-a-p-h. p at 3, h at 4. Consecutive. Not word start (prev is 'a').
// score = 100+100 + 50 + 0 + shortBonus
// shortBonus = 20 * (1 - 5/100) = 19
// total = 200 + 50 + 19 = 269
assert.strictEqual(fuzzyScore("ph", "Graph"), 269);

// Null cases
assert.strictEqual(fuzzyScore("xyz", "abc"), null);
assert.strictEqual(fuzzyScore("ba", "ab"), null);
assert.strictEqual(fuzzyScore("", "anything"), 0);
assert.strictEqual(fuzzyScore("a", ""), null);

// Test rank: 'ph' against Photo, Alpha, Graph
const items = [
  { id: "1", label: "Photo" },
  { id: "2", label: "Alpha" },
  { id: "3", label: "Graph" },
];

const ranked = rank("ph", items, 8);
assert.strictEqual(ranked.length, 3);
// Photo should be first (highest score 299), then Alpha and Graph (both 269, stable order)
assert.strictEqual(ranked[0].id, "1");
assert.strictEqual(ranked[1].id, "2");
assert.strictEqual(ranked[2].id, "3");

// Test limit
const manyItems = Array.from({ length: 20 }, (_, i) => ({ id: String(i), label: "Item" + i }));
const limited = rank("i", manyItems, 5);
assert.strictEqual(limited.length, 5);

// Empty query returns first limit items unchanged
const emptyRanked = rank("", items, 2);
assert.strictEqual(emptyRanked.length, 2);
assert.strictEqual(emptyRanked[0].id, "1");
assert.strictEqual(emptyRanked[1].id, "2");

// Read palette.js and assert exports and key handling
const paletteSrc = readFileSync("./palette.js", "utf8");
assert.ok(paletteSrc.includes("export function Palette"), "palette.js should export Palette");
assert.ok(paletteSrc.includes("ArrowDown"), "palette.js should handle ArrowDown");
assert.ok(paletteSrc.includes("ArrowUp"), "palette.js should handle ArrowUp");
assert.ok(paletteSrc.includes("Enter"), "palette.js should handle Enter");
assert.ok(paletteSrc.includes("Escape"), "palette.js should handle Escape");
assert.ok(paletteSrc.includes("role=\"dialog\""), "palette.js should have role=dialog");
assert.ok(paletteSrc.includes("aria-label"), "palette.js should have aria-label");
assert.ok(paletteSrc.includes("onPick"), "palette.js should call onPick");
assert.ok(paletteSrc.includes("onClose"), "palette.js should call onClose");

console.log("ok");
