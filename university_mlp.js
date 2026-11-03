/* ComfyUniversity: a tiny multilayer perceptron in plain JavaScript, for the "Train a tiny network" lab. No libraries and nothing fetched.
Two inputs, any number of hidden layers, one sigmoid output, binary cross-entropy, full-batch gradient descent. The backward pass is checked against
central finite differences in tests/test_university_mlp.py, and against PyTorch's autograd on the same weights. */

/* A seeded generator, so a dataset or a set of starting weights comes back the same. */
export function rng(seed) {
  let s = seed >>> 0;
  const u = () => { s = (s + 0x6D2B79F5) | 0; let t = Math.imul(s ^ (s >>> 15), 1 | s); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  const n = () => { const a = Math.max(u(), 1e-12), b = u(); return Math.sqrt(-2 * Math.log(a)) * Math.cos(2 * Math.PI * b); };
  return { u, n };
}

/* ---------- toy data: points in [-1, 1]², label 0 or 1 ---------- */
export const DATASETS = [["spiral", "Spiral"], ["circles", "Circles"], ["xor", "XOR"], ["blobs", "Two blobs"]];
export function dataset(kind, n = 240, noise = 0.1, seed = 1) {
  const r = rng(seed), X = [], y = [];
  for (let i = 0; i < n; i++) {
    const c = i % 2; let a, b;
    if (kind === "spiral") { const t = (i >> 1) / (n >> 1) * 1.75 * Math.PI + 0.3, rad = t / (1.75 * Math.PI + 0.3); a = rad * Math.cos(t + c * Math.PI); b = rad * Math.sin(t + c * Math.PI); }
    else if (kind === "circles") { const t = r.u() * 2 * Math.PI, rad = c ? 0.25 + r.u() * 0.2 : 0.65 + r.u() * 0.25; a = rad * Math.cos(t); b = rad * Math.sin(t); }
    else if (kind === "xor") { a = r.u() * 1.8 - 0.9; b = r.u() * 1.8 - 0.9; if (Math.abs(a) < 0.08) a += Math.sign(a || 1) * 0.08; if (Math.abs(b) < 0.08) b += Math.sign(b || 1) * 0.08; y.push(a * b > 0 ? 1 : 0); X.push([a + r.n() * noise * 0.5, b + r.n() * noise * 0.5]); continue; }
    else { a = (c ? 0.45 : -0.45) + r.n() * 0.22; b = (c ? 0.35 : -0.35) + r.n() * 0.22; }
    X.push([a + r.n() * noise * 0.5, b + r.n() * noise * 0.5]); y.push(c);
  }
  return { X, y };
}
/* Every fourth point held out: the network never trains on them. */
export function split(d) {
  const tr = { X: [], y: [] }, te = { X: [], y: [] };
  d.X.forEach((x, i) => { const s = i % 4 === 3 ? te : tr; s.X.push(x); s.y.push(d.y[i]); });
  return { train: tr, test: te };
}

/* ---------- activations: f(z) and f'(z) written from f's output a where that is cheaper ---------- */
export const ACTS = {
  relu: { f: (z) => (z > 0 ? z : 0), d: (z) => (z > 0 ? 1 : 0), label: "ReLU" },
  tanh: { f: (z) => Math.tanh(z), d: (z) => { const t = Math.tanh(z); return 1 - t * t; }, label: "tanh" },
  sigmoid: { f: (z) => 1 / (1 + Math.exp(-z)), d: (z) => { const s = 1 / (1 + Math.exp(-z)); return s * (1 - s); }, label: "sigmoid" },
  linear: { f: (z) => z, d: () => 1, label: "linear" },
};
export const sigmoid = (z) => (z >= 0 ? 1 / (1 + Math.exp(-z)) : Math.exp(z) / (1 + Math.exp(z)));

/* ---------- the network: W[l] is out × in, row-major; b[l] has out entries ---------- */
export function sizesOf(layers, width) { return [2, ...Array(layers).fill(width), 1]; }
export function init(sizes, act = "tanh", seed = 1) {
  const r = rng(seed), W = [], b = [];
  for (let l = 0; l + 1 < sizes.length; l++) {
    const fin = sizes[l], fout = sizes[l + 1], sd = act === "relu" ? Math.sqrt(2 / fin) : Math.sqrt(1 / fin);      // He for ReLU, LeCun-style otherwise
    W.push(Float64Array.from({ length: fin * fout }, () => r.n() * sd)); b.push(new Float64Array(fout).fill(act === "relu" && l + 2 < sizes.length ? 0.01 : 0));   // a small positive bias keeps fewer ReLUs dead, and off the kink at 0
  }
  return { sizes: sizes.slice(), act, W, b };
}
export const paramCount = (net) => net.W.reduce((t, w, l) => t + w.length + net.b[l].length, 0);
export const clone = (net) => ({ sizes: net.sizes.slice(), act: net.act, W: net.W.map((w) => Float64Array.from(w)), b: net.b.map((v) => Float64Array.from(v)) });

/* Forward pass for a batch. -> { z: pre-activations per layer, a: activations per layer (a[0] is the input), p: output probabilities } */
export function forward(net, X) {
  const L = net.W.length, f = ACTS[net.act].f, a = [X.map((x) => Float64Array.from(x))], z = [];
  for (let l = 0; l < L; l++) {
    const fin = net.sizes[l], fout = net.sizes[l + 1], W = net.W[l], bl = net.b[l], last = l === L - 1, zl = [], al = [];
    for (const v of a[l]) {
      const zz = new Float64Array(fout), aa = new Float64Array(fout);
      for (let o = 0; o < fout; o++) { let s = bl[o]; const row = o * fin; for (let i = 0; i < fin; i++) s += W[row + i] * v[i]; zz[o] = s; aa[o] = last ? sigmoid(s) : f(s); }
      zl.push(zz); al.push(aa);
    }
    z.push(zl); a.push(al);
  }
  return { z, a, p: a[L].map((v) => v[0]) };
}

/* Mean binary cross-entropy, written from the logit so it never takes log(0). */
export function loss(net, X, y, cache) {
  const c = cache || forward(net, X), zl = c.z[c.z.length - 1]; let s = 0;
  for (let k = 0; k < y.length; k++) { const t = zl[k][0]; s += Math.max(t, 0) - t * y[k] + Math.log1p(Math.exp(-Math.abs(t))); }
  return s / y.length;
}

/* Backward pass: the gradient of the mean loss for every weight and bias. Sigmoid with cross-entropy gives (p - y) at the output logit. */
export function backward(net, X, y, cache) {
  const c = cache || forward(net, X), L = net.W.length, d = ACTS[net.act].d, n = y.length;
  const gW = net.W.map((w) => new Float64Array(w.length)), gb = net.b.map((v) => new Float64Array(v.length));
  let delta = c.p.map((p, k) => Float64Array.of((p - y[k]) / n));
  for (let l = L - 1; l >= 0; l--) {
    const fin = net.sizes[l], fout = net.sizes[l + 1], W = net.W[l], next = [];
    for (let k = 0; k < n; k++) {
      const dk = delta[k], ak = c.a[l][k];
      for (let o = 0; o < fout; o++) { const g = dk[o]; if (!g) continue; gb[l][o] += g; const row = o * fin; for (let i = 0; i < fin; i++) gW[l][row + i] += g * ak[i]; }
      if (l > 0) {
        const back = new Float64Array(fin), zk = c.z[l - 1][k];
        for (let i = 0; i < fin; i++) { let s = 0; for (let o = 0; o < fout; o++) s += W[o * fin + i] * dk[o]; back[i] = s * d(zk[i]); }
        next.push(back);
      }
    }
    delta = next;
  }
  return { W: gW, b: gb };
}

/* One step of gradient descent. -> { loss before the step, mean |change| of the weights } */
export function step(net, X, y, lr) {
  const c = forward(net, X), before = loss(net, X, y, c), g = backward(net, X, y, c); let moved = 0, count = 0;
  for (let l = 0; l < net.W.length; l++) {
    for (let i = 0; i < net.W[l].length; i++) { const dw = lr * g.W[l][i]; net.W[l][i] -= dw; moved += Math.abs(dw); count++; }
    for (let i = 0; i < net.b[l].length; i++) net.b[l][i] -= lr * g.b[l][i];
  }
  return { loss: before, moved: moved / Math.max(1, count) };
}

export function accuracy(net, X, y) {
  if (!y.length) return 0; const p = forward(net, X).p; let ok = 0;
  for (let k = 0; k < y.length; k++) ok += (p[k] >= 0.5 ? 1 : 0) === y[k] ? 1 : 0;
  return ok / y.length;
}

/* Central finite differences on every parameter, against backward(). -> largest relative error, as in the CS231n notes: |a - n| / max(|a| + |n|, tiny). */
export function gradCheck(net, X, y, eps = 1e-5) {
  const g = backward(net, X, y); let worst = 0, checked = 0;
  const one = (arr, i, an) => {
    const keep = arr[i]; arr[i] = keep + eps; const up = loss(net, X, y); arr[i] = keep - eps; const dn = loss(net, X, y); arr[i] = keep;
    const num = (up - dn) / (2 * eps), rel = Math.abs(an - num) / Math.max(Math.abs(an) + Math.abs(num), 1e-12);
    if (Math.abs(an) + Math.abs(num) > 1e-9) worst = Math.max(worst, rel); checked++;
  };
  for (let l = 0; l < net.W.length; l++) { for (let i = 0; i < net.W[l].length; i++) one(net.W[l], i, g.W[l][i]); for (let i = 0; i < net.b[l].length; i++) one(net.b[l], i, g.b[l][i]); }
  return { worst, checked };
}

/* The network's probability on a res × res grid over [-lim, lim]², top row first, for the decision boundary. */
export function field(net, res = 48, lim = 1.2) {
  const pts = [];
  for (let j = 0; j < res; j++) for (let i = 0; i < res; i++) pts.push([-lim + (i + 0.5) / res * 2 * lim, lim - (j + 0.5) / res * 2 * lim]);
  return Float64Array.from(forward(net, pts).p);
}
