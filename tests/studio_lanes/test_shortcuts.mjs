import assert from "node:assert";
import { parseCombo, matches, isTyping, createRegistry } from "./shortcuts_logic.js";

// Test parseCombo
const combo1 = parseCombo("ctrl+k");
assert.strictEqual(combo1.key, "k");
assert.strictEqual(combo1.ctrl, true);
assert.strictEqual(combo1.shift, false);
assert.strictEqual(combo1.alt, false);
assert.strictEqual(combo1.meta, false);

const combo2 = parseCombo("mod+s", true);
assert.strictEqual(combo2.key, "s");
assert.strictEqual(combo2.ctrl, false);
assert.strictEqual(combo2.meta, true);

const combo3 = parseCombo("mod+s", false);
assert.strictEqual(combo3.key, "s");
assert.strictEqual(combo3.ctrl, true);
assert.strictEqual(combo3.meta, false);

const combo4 = parseCombo("shift+alt+z");
assert.strictEqual(combo4.key, "z");
assert.strictEqual(combo4.shift, true);
assert.strictEqual(combo4.alt, true);
assert.strictEqual(combo4.ctrl, false);
assert.strictEqual(combo4.meta, false);

// Test matches
const event1 = { key: "k", ctrlKey: true, shiftKey: false, altKey: false, metaKey: false };
assert.strictEqual(matches(combo1, event1), true);

const event2 = { key: "k", ctrlKey: false, shiftKey: false, altKey: false, metaKey: false };
assert.strictEqual(matches(combo1, event2), false);

const event3 = { key: "s", ctrlKey: false, shiftKey: false, altKey: false, metaKey: true };
assert.strictEqual(matches(combo2, event3), true);

// Test isTyping
assert.strictEqual(isTyping({ tagName: "INPUT", isContentEditable: false }), true);
assert.strictEqual(isTyping({ tagName: "TEXTAREA", isContentEditable: false }), true);
assert.strictEqual(isTyping({ tagName: "SELECT", isContentEditable: false }), true);
assert.strictEqual(isTyping({ tagName: "DIV", isContentEditable: true }), true);
assert.strictEqual(isTyping({ tagName: "DIV", isContentEditable: false }), false);
assert.strictEqual(isTyping({ tagName: "BUTTON", isContentEditable: false }), false);

// Test createRegistry
const registry = createRegistry();
let called1 = false;
let called2 = false;

const result1 = registry.add("ctrl+k", "id1", "Label 1", () => { called1 = true; });
assert.strictEqual(result1.conflict, false);

const result2 = registry.add("ctrl+k", "id2", "Label 2", () => { called2 = true; });
assert.strictEqual(result2.conflict, true);
assert.strictEqual(result2.combo, "ctrl+k");
assert.strictEqual(result2.existingId, "id1");

const list = registry.list();
assert.strictEqual(list.length, 1);
assert.strictEqual(list[0].id, "id1");
assert.strictEqual(list[0].label, "Label 1");
assert.strictEqual(list[0].combo, "ctrl+k");

// Test handle - should not run when typing and no ctrl/meta
const eventTyping = { key: "k", ctrlKey: false, shiftKey: false, altKey: false, metaKey: false, target: { tagName: "INPUT", isContentEditable: false } };
const handled1 = registry.handle(eventTyping);
assert.strictEqual(handled1, false);
assert.strictEqual(called1, false);

// Test handle - should run when not typing
const eventNotTyping = { key: "k", ctrlKey: true, shiftKey: false, altKey: false, metaKey: false, target: { tagName: "DIV", isContentEditable: false } };
const handled2 = registry.handle(eventNotTyping);
assert.strictEqual(handled2, true);
assert.strictEqual(called1, true);

// Test handle - should run when typing but with ctrl
const eventTypingCtrl = { key: "k", ctrlKey: true, shiftKey: false, altKey: false, metaKey: false, target: { tagName: "INPUT", isContentEditable: false } };
const handled3 = registry.handle(eventTypingCtrl);
assert.strictEqual(handled3, true);

console.log("ok");
