import { readFileSync } from 'fs';
import assert from 'node:assert';

const code = readFileSync('timeline_ui.js', 'utf8');

assert(code.includes('export function Timeline'), 'Missing export function Timeline');
assert(code.includes('from "preact"'), 'Missing import from preact');
assert(code.includes('from "preact/hooks"'), 'Missing import from preact/hooks');
assert(code.includes('from "htm"'), 'Missing import from htm');
assert(code.includes("from './timeline_core.js'"), 'Missing import from ./timeline_core.js');

assert(code.includes('moveClip'), 'Missing moveClip');
assert(code.includes('trimClip'), 'Missing trimClip');
assert(code.includes('splitAt'), 'Missing splitAt');
assert(code.includes('toEDL'), 'Missing toEDL');
assert(code.includes('validateEDL'), 'Missing validateEDL');
assert(code.includes('onRender'), 'Missing onRender');

// Strip strings, template literals, and comments to check balance
let stripped = code
  .replace(/\/\*[\s\S]*?\*\//g, '') // block comments
  .replace(/\/\/.*$/gm, '') // line comments
  .replace(/`(?:\\.|[^`\\])*`/g, '``') // template literals
  .replace(/'(?:\\.|[^'\\])*'/g, "''") // single quotes
  .replace(/"(?:\\.|[^"\\])*"/g, '""'); // double quotes

let parens = 0, brackets = 0, braces = 0;
for (const ch of stripped) {
  if (ch === '(') parens++;
  if (ch === ')') parens--;
  if (ch === '[') brackets++;
  if (ch === ']') brackets--;
  if (ch === '{') braces++;
  if (ch === '}') braces--;
  assert(parens >= 0, 'Unbalanced parentheses');
  assert(brackets >= 0, 'Unbalanced brackets');
  assert(braces >= 0, 'Unbalanced braces');
}
assert(parens === 0, 'Unbalanced parentheses at end');
assert(brackets === 0, 'Unbalanced brackets at end');
assert(braces === 0, 'Unbalanced braces at end');

console.log('ok');
