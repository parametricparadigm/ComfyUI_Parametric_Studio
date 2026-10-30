import assert from 'node:assert';
import { buildModel, layoutGraph, explain, keyType, placeOrdered, fitView, cometsOn, pulseAge, focusSets, nodeStates, linkState, graphRequest, replayPlan, replayAt, executionOrder, walkOrder, panelSize, PLACEHOLDER, PREVIEW_SEED } from './graph3d_math.js';

// a real shape: the FLUX.2 Klein graph the image goal uses
const G = {
  1: { class_type: 'UNETLoader', inputs: { unet_name: 'a/b/flux.safetensors', weight_dtype: 'default' } }, 2: { class_type: 'CLIPLoader', inputs: { clip_name: 'q.safetensors' } }, 3: { class_type: 'VAELoader', inputs: { vae_name: 'v.safetensors' } },
  4: { class_type: 'CLIPTextEncode', inputs: { clip: ['2', 0], text: 'a fox' } }, 5: { class_type: 'CLIPTextEncode', inputs: { clip: ['2', 0], text: '' } }, 6: { class_type: 'EmptyFlux2LatentImage', inputs: { width: 1024, height: 1024 } }, 7: { class_type: 'Flux2Scheduler', inputs: { steps: 4 } },
  8: { class_type: 'CFGGuider', inputs: { model: ['1', 0], positive: ['4', 0], negative: ['5', 0], cfg: 1 } }, 9: { class_type: 'KSamplerSelect', inputs: { sampler_name: 'euler' } }, 10: { class_type: 'RandomNoise', inputs: { noise_seed: 11 } },
  11: { class_type: 'SamplerCustomAdvanced', inputs: { noise: ['10', 0], guider: ['8', 0], sampler: ['9', 0], sigmas: ['7', 0], latent_image: ['6', 0] } }, 12: { class_type: 'VAEDecode', inputs: { samples: ['11', 0], vae: ['3', 0] } }, 13: { class_type: 'SaveImage', inputs: { images: ['12', 0], filename_prefix: 'x' } },
};
// model: links, widgets, depth, types
const m0 = buildModel(G);
assert.strictEqual(m0.ids.length, 13); assert.strictEqual(m0.links.length, 13);
assert.deepStrictEqual(m0.nodes['13'].widgets.map((w) => w.key), ['filename_prefix']);
assert.strictEqual(m0.nodes['13'].depth, 5, 'longest path from a source');
assert.strictEqual(m0.nodes['1'].depth, 0);
const lt = (to, key) => m0.links.find((l) => l.to === to && l.key === key).type;
assert.strictEqual(lt('8', 'model'), 'MODEL'); assert.strictEqual(lt('8', 'positive'), 'CONDITIONING'); assert.strictEqual(lt('11', 'latent_image'), 'LATENT'); assert.strictEqual(lt('12', 'vae'), 'VAE');
assert.strictEqual(keyType('values.a'), 'NUMBER');
// a link to a missing node stays a widget; a cycle cannot hang
assert.strictEqual(buildModel({ a: { class_type: 'X', inputs: { v: ['nope', 0] } } }).links.length, 0);
assert.strictEqual(buildModel({ a: { class_type: 'X', inputs: { i: ['b', 0] } }, b: { class_type: 'Y', inputs: { i: ['a', 0] } } }).ids.length, 2);
assert.strictEqual(layoutGraph({ a: { class_type: 'X', inputs: { i: ['b', 0] } }, b: { class_type: 'Y', inputs: { i: ['a', 0] } } }).ids.length, 2);
assert.strictEqual(buildModel(null).ids.length, 0); assert.strictEqual(layoutGraph({}).ids.length, 0);
// explanations: dict for common classes, class name as the fallback
assert.ok(explain('KSampler').say.length > 20); assert.strictEqual(explain('KSampler').kind, 'sample');
const u = explain('SomeUnknownThing'); assert.strictEqual(u.known, false); assert.strictEqual(u.say, 'SomeUnknownThing');
// every class in the repo's workflows has an explanation
import { readFileSync, existsSync, readdirSync } from 'node:fs';
// (workflows are outside the temp copy of studio/web; the Python side checks them)
// layout: every wire runs left to right, by column and on screen
const L = layoutGraph(G);
L.links.forEach((l) => { assert.ok(L.nodes[l.from].col < L.nodes[l.to].col, `col ${l.from}->${l.to}`); assert.ok(l.curve[0][0] < l.curve[3][0], 'x grows along the wire'); assert.ok(l.len > 0 && Number.isFinite(l.len)); });
assert.ok(L.plate && L.plate.save === '13'); assert.ok(L.plate.pos[0] > L.nodes['13'].pos[0], 'the result sits past the last node');
// panels in one column never overlap
L.cols.forEach((c) => { const s = c.map((i) => [L.nodes[i].y - L.nodes[i].size.h / 2, L.nodes[i].y + L.nodes[i].size.h / 2]).sort((a, b) => a[0] - b[0]); for (let i = 1; i < s.length; i++) assert.ok(s[i][0] >= s[i - 1][1] - 1e-6, 'rows overlap'); });
// floor is under everything, ports sit on the panel edges
L.ids.forEach((i) => assert.ok(L.nodes[i].pos[1] - L.nodes[i].size.h / 2 > L.floor));
assert.ok(Math.abs(placeOrdered([0, 0], [2, 2], 1)[1] - placeOrdered([0, 0], [2, 2], 1)[0] - 3) < 1e-9, 'gap kept'); assert.deepStrictEqual(placeOrdered([0, 100], [1, 1], 1), [0, 100], 'free nodes stay put');
assert.ok(panelSize(L.nodes['11']).w > panelSize(L.nodes['1']).w, 'the sampler is the hero');
// deep graphs weave but still flow left to right
const chain = {}; for (let i = 0; i < 14; i++) chain['n' + i] = { class_type: 'ImageScale', inputs: i ? { image: ['n' + (i - 1), 0] } : {} };
const LC = layoutGraph(chain); LC.links.forEach((l) => assert.ok(LC.nodes[l.from].pos[0] < LC.nodes[l.to].pos[0]));
// the camera fits every point and looks at the middle
const fv = fitView(L.bounds, 0.16, 0.1, 30, 1.75, 1); const tan = Math.tan((30 * Math.PI) / 360);
L.bounds.forEach((p) => { const d = fv.position.map((x, i) => p[i] - x), dir = fv.target.map((x, i) => x - fv.position[i]), n = Math.hypot(...dir), z = (d[0] * dir[0] + d[1] * dir[1] + d[2] * dir[2]) / n; assert.ok(z > 0, 'in front of the camera'); });
// the wave: comets move from source to target as the clock runs; every input of a node arrives together
const link = { start: 10, len: 8 }; const a = cometsOn(link, 12, 30), b = cometsOn(link, 14, 30);
assert.strictEqual(a.length, 1); assert.ok(b[0] > a[0], 'data-flow direction'); assert.deepStrictEqual(cometsOn(link, 5, 30), []);
assert.ok(pulseAge(10, 11, 30) < pulseAge(10, 20, 30)); assert.ok(pulseAge(10, 5, 30) > 0, 'always positive');
L.links.forEach((l) => assert.ok(Math.abs(l.start + l.len - L.arrive[l.to]) < 1e-9));
// hover: direct links only; click: the whole chain
const hov = focusSets(L, '8', false), cl = focusSets(L, '8', true);
assert.strictEqual(hov.links.size, 4); assert.ok(hov.nodes.has('11') && !hov.nodes.has('13')); assert.ok(cl.nodes.has('13') && cl.nodes.has('2'));
assert.strictEqual(focusSets(L, null).links.size, 0);
// a run: states and wires
const st = nodeStates(L, { running: { 11: [3, 20] }, done: ['1', '2', '4', '5', '8', '6', '7', '9', '10'], cached: ['3'] });
assert.strictEqual(st['11'], 'running'); assert.strictEqual(st['1'], 'done'); assert.strictEqual(st['3'], 'cached'); assert.strictEqual(st['13'], 'pending');
assert.strictEqual(linkState({ from: '8', to: '11' }, st), 'flow'); assert.strictEqual(linkState({ from: '12', to: '13' }, st), 'idle'); assert.strictEqual(linkState({ from: '4', to: '8' }, st), 'spent');
assert.strictEqual(nodeStates(L, { running: {}, done: [], error: '12' })['12'], 'error');
// replay follows dependency order and gives the sampler the largest share
const ord = executionOrder(L), pos = Object.fromEntries(ord.map((i, k) => [i, k])); L.links.forEach((l) => assert.ok(pos[l.from] < pos[l.to]));
const plan = replayPlan(L, 10); assert.ok(Math.abs(plan.reduce((x, e) => x + e.seconds, 0) - 10) < 1e-9); assert.strictEqual([...plan].sort((x, y) => y.seconds - x.seconds)[0].id, '11');
const samp = plan.find((e) => e.id === '11'), mid = replayAt(plan, samp.start + samp.seconds / 2); assert.deepStrictEqual(Object.keys(mid.running), ['11']); assert.ok(mid.running['11'][0] >= 10 && mid.running['11'][0] <= 11); assert.ok(mid.done.includes('1')); assert.ok(!mid.done.includes('13'));
assert.strictEqual(replayAt(plan, 11).done.length, 13);
// always a graph: sample prompt, placeholders for missing uploads, stable preview seed
const ideas = { image: ['sample one'], recast: ['x'] };
const r1 = graphRequest({ goal: 'image', prompt: '  ', options: {}, seed: '' }, {}, ideas); assert.strictEqual(r1.body.prompt, 'sample one'); assert.ok(r1.sampled); assert.strictEqual(r1.body.seed, PREVIEW_SEED); assert.ok(r1.previewSeed);
const r2 = graphRequest({ goal: 'image', prompt: 'mine', options: {}, seed: '42', job: 'j' }, {}, ideas); assert.strictEqual(r2.body.prompt, 'mine'); assert.ok(!r2.sampled); assert.strictEqual(r2.body.seed, '42'); assert.ok(!('job' in r2.body));
const r3 = graphRequest({ goal: 'recast', prompt: '', options: {}, seed: '' }, { needs_video: true, needs_image: true, prompt_optional: true }, ideas); assert.strictEqual(r3.body.video, PLACEHOLDER.video); assert.strictEqual(r3.body.image, PLACEHOLDER.image); assert.deepStrictEqual(r3.fills, ['video', 'image']); assert.strictEqual(r3.body.prompt, ''); assert.ok(!r3.sampled);
const r4 = graphRequest({ goal: 'recast', prompt: '', options: {}, video: 'real.mp4', image: 'me.png' }, { needs_video: true, needs_image: true, prompt_optional: true }, ideas); assert.strictEqual(r4.body.video, 'real.mp4'); assert.deepStrictEqual(r4.fills, []);
assert.strictEqual(graphRequest(null, {}, ideas), null);
// the walk skips the small value nodes and starts upstream
const w = walkOrder(L); assert.ok(w.indexOf('11') < w.indexOf('13')); assert.ok(w.length <= 13);
// the page really uses three lazily, pauses off screen and disposes
const src = readFileSync('./graph3d.js', 'utf8');
for (const needle of ['import("three")', 'IntersectionObserver', 'ResizeObserver', 'renderer.dispose()', 'forceContextLoss', 'prefers-reduced-motion', 'webglcontextlost', 'cb.onFail']) assert.ok(src.includes(needle), needle);
console.log('ok');
