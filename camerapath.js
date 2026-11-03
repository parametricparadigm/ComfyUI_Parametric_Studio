/* Camera Paths: draw the camera's move on a globe around the subject, or a line for something to follow, render it, and check any take against the move you asked for.
   The 3D view is three.js (vendored); every key can also be set with plain sliders, so the page works with a keyboard and without WebGL. */
import { useEffect, useRef, useState } from "preact/hooks";
import { html, api, post } from "./common.js";
import { FxSkeleton } from "./fx.js";
import { addKey, confusion, globePath, globePos, LINE_PRESETS, lineLength, MAX_KEYS, moveWord, presetKeys, removeKey, RADIUS, SUBJECT, thin, tidyKey, toThree, VERDICT_CLASS, verdictWord } from "./camerapath_logic.js";

const said = (e) => (e && e.message) || String(e || "");
const viewUrl = (file) => { const i = file.lastIndexOf("/"); return "/api/view?" + new URLSearchParams({ filename: file.slice(i + 1), subfolder: i > 0 ? file.slice(0, i) : "", type: "output" }); };
const Verdict = ({ v }) => html`<span class=${"fx-tag " + (VERDICT_CLASS[v] || "")}>${verdictWord(v)}</span>`;
const AiMark = () => html`<span class="fx-tag" title="Made by a model on this machine">AI-generated</span>`;

function usePoll(job, setJob) {
  useEffect(() => {
    if (!job || job.status !== "running") return undefined;
    const t = setInterval(() => api("/api/campath/jobs/" + job.job).then(setJob).catch(() => {}), 2500);
    return () => clearInterval(t);
  }, [job]);
}

function Upload({ label, accept, value, onDone }) {
  const [err, setErr] = useState(""), [busy, setBusy] = useState(false);
  const pick = async (e) => {
    const f = e.target.files[0]; if (!f) return; setErr(""); setBusy(true);
    const fd = new FormData(); fd.append("file", f);
    try { const r = await api("/api/upload", { method: "POST", body: fd }); onDone(r.name, URL.createObjectURL(f)); } catch (x) { setErr(said(x)); }
    setBusy(false);
  };
  return html`<label class="fx-lab">${label}<input class="fx-in" type="file" accept=${accept} onChange=${pick} disabled=${busy}/>${value && html`<small>Added: ${value}</small>`}${err && html`<small class="fx-err" role="alert">${err}</small>`}</label>`;
}

/* ---------- the 3D globe */
function Globe({ keys, setKeys, positions, playing }) {
  const box = useRef(null), st = useRef({}), [noGl, setNoGl] = useState(false);
  useEffect(() => {
    let alive = true, raf = 0;
    (async () => {
      let THREE, OrbitControls;
      try { THREE = await import("three"); ({ OrbitControls } = await import("three/addons/controls/OrbitControls.js")); } catch { setNoGl(true); return; }
      if (!alive || !box.current) return;
      let renderer;
      try { renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true }); } catch { setNoGl(true); return; }
      const el = box.current, scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(45, 1, 0.1, 200);
      renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1)); el.appendChild(renderer.domElement); renderer.domElement.setAttribute("aria-hidden", "true");
      cam.position.set(9, 7, 4); const ctl = new OrbitControls(cam, renderer.domElement); ctl.target.set(0, 0, -SUBJECT); ctl.enableDamping = true; ctl.update();
      scene.add(new THREE.HemisphereLight(0xffffff, 0x334433, 1.4));
      const grid = new THREE.GridHelper(16, 16, 0x666666, 0x333333); grid.position.set(0, -1.2, -SUBJECT); scene.add(grid);
      const subject = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.45, 2.2, 16), new THREE.MeshStandardMaterial({ color: 0xd4af37 })); subject.position.set(0, -0.1, -SUBJECT); scene.add(subject);
      const globe = new THREE.Mesh(new THREE.SphereGeometry(RADIUS, 32, 16), new THREE.MeshBasicMaterial({ color: 0x2ecc71, wireframe: true, transparent: true, opacity: 0.18 })); globe.position.set(0, 0, -SUBJECT); scene.add(globe);
      const line = new THREE.Line(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ color: 0xf5c518 })); scene.add(line);
      const camMark = new THREE.Mesh(new THREE.ConeGeometry(0.28, 0.6, 4), new THREE.MeshStandardMaterial({ color: 0xffffff })); scene.add(camMark);
      const dots = new THREE.Group(); scene.add(dots);
      const ray = new THREE.Raycaster(), ptr = new THREE.Vector2(); let drag = -1;
      const at = (e) => { const r = renderer.domElement.getBoundingClientRect(); ptr.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1); ray.setFromCamera(ptr, cam); };
      const down = (e) => { at(e); const hit = ray.intersectObjects(dots.children)[0]; if (hit && hit.object.userData.i > 0) { drag = hit.object.userData.i; ctl.enabled = false; renderer.domElement.setPointerCapture(e.pointerId); } };
      const move = (e) => {
        if (drag < 0) return; at(e); const hit = ray.intersectObject(globe)[0]; if (!hit) return;
        const p = hit.point, x = p.x, y = -p.y, z = -p.z, dz = SUBJECT - z;      // three -> node axes
        const k = tidyKey({ round: (Math.atan2(x, dz) * 180) / Math.PI, up: (Math.atan2(-y, Math.hypot(x, dz)) * 180) / Math.PI });
        st.current.setKeys((ks) => ks.map((o, j) => (j === drag ? k : o)));
      };
      const up = () => { drag = -1; ctl.enabled = true; };
      renderer.domElement.addEventListener("pointerdown", down); renderer.domElement.addEventListener("pointermove", move); renderer.domElement.addEventListener("pointerup", up); renderer.domElement.addEventListener("pointercancel", up);
      const size = () => { const w = el.clientWidth, h = Math.max(240, Math.round(w * 0.62)); renderer.setSize(w, h); cam.aspect = w / h; cam.updateProjectionMatrix(); };
      const ro = new ResizeObserver(size); ro.observe(el); size();
      let t0 = performance.now(), seen = true; const io = new IntersectionObserver((es) => { seen = es[0].isIntersecting; }); io.observe(el);
      const tick = (now) => {
        if (!alive) return; raf = requestAnimationFrame(tick); if (!seen) return; ctl.update();
        const s = st.current, pos = s.positions || [];
        if (pos.length) {
          const f = s.playing ? ((now - t0) / 4000) % 1 : 0, i = Math.min(pos.length - 1, Math.floor(f * (pos.length - 1))), p = toThree(pos[i]);
          camMark.position.set(p[0], p[1], p[2]); camMark.lookAt(0, 0, -SUBJECT); camMark.rotateX(Math.PI / 2);
        }
        renderer.render(scene, cam);
      };
      raf = requestAnimationFrame(tick);
      st.current = { ...st.current, THREE, line, dots, cleanup: () => { ro.disconnect(); io.disconnect(); ctl.dispose(); renderer.dispose(); renderer.domElement.remove(); } };
      st.current.redraw && st.current.redraw();
    })();
    return () => { alive = false; cancelAnimationFrame(raf); st.current.cleanup && st.current.cleanup(); };
  }, []);
  st.current.setKeys = setKeys; st.current.positions = positions; st.current.playing = playing;
  st.current.redraw = () => {
    const { THREE, line, dots } = st.current; if (!THREE) return;
    line.geometry.dispose(); line.geometry = new THREE.BufferGeometry().setFromPoints((positions || []).map((p) => new THREE.Vector3(...toThree(p))));
    dots.children.forEach((d) => d.geometry.dispose()); dots.clear();
    keys.forEach((k, i) => { const m = new THREE.Mesh(new THREE.SphereGeometry(i ? 0.22 : 0.17, 16, 8), new THREE.MeshStandardMaterial({ color: i ? 0xf5c518 : 0xffffff })); m.position.set(...toThree(globePos(k.round, k.up))); m.userData.i = i; dots.add(m); });
  };
  useEffect(() => { st.current.redraw(); }, [keys, positions]);
  return html`<div class="cp-globe" ref=${box}>${noGl && html`<p class="small" role="status">This browser has no 3D view here. Set the keys with the sliders below: they draw the same path.</p>`}</div>`;
}

function KeySliders({ keys, setKeys }) {
  const set = (i, f, v) => setKeys((ks) => ks.map((k, j) => (j === i ? tidyKey({ ...k, [f]: v }) : k)));
  return html`<ol class="cp-keys">${keys.map((k, i) => html`<li key=${i}>
    <b>${i === 0 ? "Start" : "Key " + i}</b>
    ${i === 0 ? html`<small>where the shot begins, facing the subject</small>` : html`
      <label class="fx-lab">Round (${k.round}°)<input type="range" min="-170" max="170" value=${k.round} onInput=${(e) => set(i, "round", e.target.value)} aria-label=${`Key ${i}: degrees round the subject`}/></label>
      <label class="fx-lab">Up (${k.up}°)<input type="range" min="-10" max="70" value=${k.up} onInput=${(e) => set(i, "up", e.target.value)} aria-label=${`Key ${i}: degrees up`}/></label>
      <button class="btn small" type="button" onClick=${() => setKeys((ks) => removeKey(ks, i))} disabled=${keys.length <= 2} aria-label=${`Remove key ${i}`}>Remove</button>`}
  </li>`)}</ol>`;
}

function DrawMove({ info }) {
  const [keys, setKeys] = useState([{ round: 0, up: 0 }, { round: 20, up: 0 }, { round: 40, up: 0 }]), [plan, setPlan] = useState(null), [err, setErr] = useState(""), [playing, setPlaying] = useState(() => !matchMedia("(prefers-reduced-motion: reduce)").matches);
  const [image, setImage] = useState(""), [preview, setPreview] = useState(""), [prompt, setPrompt] = useState(""), [seed, setSeed] = useState(""), [job, setJob] = useState(null), [busy, setBusy] = useState(false);
  usePoll(job, setJob);
  useEffect(() => { const t = setTimeout(() => post("/api/campath/plan", { path: globePath(keys) }).then((p) => { setPlan(p); setErr(""); }).catch((e) => setErr(said(e))), 200); return () => clearTimeout(t); }, [keys]);
  const presets = Object.entries(info.presets || {}).map(([id, p]) => ({ id, label: p.label, keys: presetKeys(p.path) })).filter((p) => p.keys);
  const go = async () => { setBusy(true); setErr(""); try { setJob(await post("/api/campath/render", { kind: "wan_path", path: globePath(keys), image, prompt, seed: Number(seed) || undefined })); } catch (e) { setErr(said(e)); } setBusy(false); };
  const r = info.renders && info.renders.wan_path;
  return html`<section class="fx-card" aria-labelledby="cp-draw"><span class="fx-kick">Camera path</span><h2 id="cp-draw">Draw the camera's move</h2>
    <p class="small">The gold post is your subject. Drag the gold dots over the globe to move the camera round and up, and the path is the yellow line. The white dot is where the shot starts.</p>
    <div class="fx-row">${presets.map((p) => html`<button key=${p.id} class="btn small" type="button" onClick=${() => setKeys(p.keys)}>${p.label}</button>`)}<button class="btn small" type="button" onClick=${() => setKeys((k) => addKey(k))} disabled=${keys.length >= MAX_KEYS}>Add a key</button><button class="btn small" type="button" aria-pressed=${playing} onClick=${() => setPlaying(!playing)}>${playing ? "Stop preview" : "Play preview"}</button></div>
    <${Globe} keys=${keys} setKeys=${setKeys} positions=${plan && plan.positions} playing=${playing}/>
    <${KeySliders} keys=${keys} setKeys=${setKeys}/>
    ${plan && html`<p role="status"><b>The checker will expect: ${moveWord(plan.expect)}.</b> <span class="small">On screen, the far background should move ${Math.round(Math.abs(plan.background.dx) * 50)}% of the width ${plan.background.dx >= 0 ? "right" : "left"} while the subject ${Math.abs(plan.subject.dx) < 0.08 ? "stays in the middle" : "slides too"}.</span></p>`}
    ${err && html`<p class="fx-err" role="alert">${err}</p>`}
    <div class="cp-form">
      <${Upload} label="Start picture (the subject in the middle)" accept="image/png,image/jpeg,image/webp" value=${image} onDone=${(n, u) => { setImage(n); setPreview(u); }}/>
      ${preview && html`<img class="cp-thumb" src=${preview} alt="The start picture you added"/>`}
      <label class="fx-lab" for="cp-wan-p">Describe the scene<textarea id="cp-wan-p" class="fx-in" rows="3" maxlength="800" value=${prompt} onInput=${(e) => setPrompt(e.target.value)}></textarea></label>
      <label class="fx-lab" for="cp-wan-s">Seed (blank for 7)<input id="cp-wan-s" class="fx-in" inputmode="numeric" value=${seed} onInput=${(e) => setSeed(e.target.value.replace(/\D/g, ""))}/></label>
      <button class="fx-go" type="button" onClick=${go} disabled=${busy || !image || !prompt.trim() || (job && job.status === "running")}>Render this path</button>
      ${r && html`<p class="small">${r.model}, ${r.size[0]}×${r.size[1]}, ${r.frames} frames at ${r.fps} fps. Needs about ${r.peak_gb} GB of graphics memory. Licence: ${r.licence}.</p>`}
    </div>
    <${JobView} job=${job}/>
  </section>`;
}

/* ---------- a line for an object to follow */
function DrawLine({ info }) {
  const [image, setImage] = useState(""), [preview, setPreview] = useState(""), [lines, setLines] = useState([]), [cur, setCur] = useState(null), [prompt, setPrompt] = useState(""), [seed, setSeed] = useState(""), [job, setJob] = useState(null), [err, setErr] = useState(""), [busy, setBusy] = useState(false);
  const pad = useRef(null); usePoll(job, setJob);
  const rel = (e) => { const r = pad.current.getBoundingClientRect(); return [(e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height]; };
  const down = (e) => { if (lines.length >= 3) return; pad.current.setPointerCapture(e.pointerId); setCur([rel(e)]); };
  const move = (e) => { if (cur) setCur((c) => [...c, rel(e)]); };
  const up = () => { if (!cur) return; const t = thin(cur); if (t.length >= 2 && lineLength(t) > 0.03) setLines((l) => [...l, t]); setCur(null); };
  const d = (pts) => pts.map((p, i) => `${i ? "L" : "M"}${(p[0] * 960).toFixed(1)} ${(p[1] * 576).toFixed(1)}`).join(" ");
  const go = async () => { setBusy(true); setErr(""); try { setJob(await post("/api/campath/render", { kind: "ltx_track", tracks: lines, image, prompt, seed: Number(seed) || undefined })); } catch (e) { setErr(said(e)); } setBusy(false); };
  const r = info.renders && info.renders.ltx_track;
  return html`<section class="fx-card" aria-labelledby="cp-line"><span class="fx-kick">Motion path</span><h2 id="cp-line">Draw where something goes</h2>
    <p class="small">Add a picture, then draw from the thing you want to move to where it should go. Up to three lines. The first point of each line should sit on the thing itself.</p>
    <${Upload} label="Picture" accept="image/png,image/jpeg,image/webp" value=${image} onDone=${(n, u) => { setImage(n); setPreview(u); setLines([]); }}/>
    <div class="cp-pad" ref=${pad} onPointerDown=${down} onPointerMove=${move} onPointerUp=${up} onPointerCancel=${up} role="img" aria-label=${`Drawing area: ${lines.length} line${lines.length === 1 ? "" : "s"} drawn`}>
      ${preview ? html`<img src=${preview} alt=""/>` : html`<span class="small">Add a picture to draw on</span>`}
      <svg viewBox="0 0 960 576" preserveAspectRatio="none" aria-hidden="true">${[...lines, ...(cur ? [cur] : [])].map((l, i) => html`<g key=${i}><path d=${d(l)} class="cp-path"/><circle cx=${l[0][0] * 960} cy=${l[0][1] * 576} r="9" class="cp-start"/></g>`)}</svg>
    </div>
    <div class="fx-row">${Object.entries(LINE_PRESETS).map(([k, p]) => html`<button key=${k} class="btn small" type="button" disabled=${lines.length >= 3} onClick=${() => setLines((l) => [...l, p.pts])}>${p.label}</button>`)}<button class="btn small" type="button" onClick=${() => setLines([])} disabled=${!lines.length}>Clear lines</button></div>
    <label class="fx-lab" for="cp-ltx-p">Describe the scene and the motion<textarea id="cp-ltx-p" class="fx-in" rows="3" maxlength="800" value=${prompt} onInput=${(e) => setPrompt(e.target.value)}></textarea></label>
    <label class="fx-lab" for="cp-ltx-s">Seed (blank for 7)<input id="cp-ltx-s" class="fx-in" inputmode="numeric" value=${seed} onInput=${(e) => setSeed(e.target.value.replace(/\D/g, ""))}/></label>
    <button class="fx-go" type="button" onClick=${go} disabled=${busy || !image || !lines.length || !prompt.trim() || (job && job.status === "running")}>Render with these lines</button>
    ${r && html`<p class="small">${r.model}, ${r.size[0]}×${r.size[1]}, ${r.frames} frames at ${r.fps} fps. Needs about ${r.peak_gb} GB of graphics memory. Licence: ${r.licence}.</p>`}
    ${err && html`<p class="fx-err" role="alert">${err}</p>`}
    <${JobView} job=${job}/>
  </section>`;
}

function JobView({ job }) {
  if (!job) return null;
  if (job.status === "running") return html`<p role="status" class="small">Rendering. This can take a few minutes.</p>`;
  if (job.status === "error") return html`<p class="fx-err" role="alert">${job.error}</p>`;
  return html`<figure class="cp-result"><video src=${viewUrl(job.file)} controls playsinline loop></video>
    <figcaption><${AiMark}/> ${job.verdict && html`<${Verdict} v=${job.verdict}/> <span>expected ${moveWord(job.expect)}: ${job.why}</span>`}
    ${job.follow && html`<span>Followed the line within ${job.follow.mean_px} px on average (worst ${job.follow.max_px} px)${job.follow.lost_at != null ? `, lost at frame ${job.follow.lost_at}` : ""}.</span>`}
    <small>${job.model}, seed ${job.seed}, ${job.seconds} s.</small></figcaption></figure>`;
}

/* ---------- checking takes */
function Check({ info }) {
  const [clips, setClips] = useState([]), [chosen, setChosen] = useState([]), [move, setMove] = useState("dolly_in"), [res, setRes] = useState(null), [err, setErr] = useState(""), [busy, setBusy] = useState(false);
  useEffect(() => {
    api("/api/history?limit=60&only=main").then((rows) => setClips(rows.flatMap((r) => (r.files || []).filter((f) => f.kind === "video").map((f) => ({ id: (f.subfolder ? f.subfolder + "/" : "") + f.filename, label: f.filename, url: f.url, prompt: r.prompt || "" })))).slice(0, 40)).catch((e) => setErr(said(e)));
  }, []);
  const toggle = (id) => setChosen((c) => (c.includes(id) ? c.filter((x) => x !== id) : c.length < 12 ? [...c, id] : c));
  const go = async () => {
    setBusy(true); setErr(""); setRes(null);
    try { setRes(chosen.length === 1 ? { picked: null, results: [{ take: chosen[0], ...(await post("/api/campath/verify", { clip: chosen[0], move })) }], single: true } : await post("/api/campath/pick", { clips: chosen, move })); } catch (e) { setErr(said(e)); }
    setBusy(false);
  };
  return html`<section class="fx-card" aria-labelledby="cp-check"><span class="fx-kick">Checker</span><h2 id="cp-check">Did the take do the move?</h2>
    <p class="small">Pick one take to check, or several to pick the one that followed the move best. This runs on the processor, not the graphics card. ${Object.entries(info.verdicts || {}).map(([k, v]) => html`<span key=${k}><${Verdict} v=${k}/> ${v} </span>`)}</p>
    <label class="fx-lab" for="cp-move">The move you asked for<select id="cp-move" class="fx-in" value=${move} onChange=${(e) => setMove(e.target.value)}>${(info.moves || []).map((m) => html`<option key=${m.id} value=${m.id}>${m.label}${m.readable ? "" : " (cannot be read)"}</option>`)}</select></label>
    <fieldset class="cp-clips"><legend class="small">Takes from this studio, newest first (${chosen.length} picked)</legend>
      ${clips.length === 0 && html`<p class="small">No clips made here yet.</p>`}
      ${clips.map((c) => html`<label key=${c.id} class="cp-clip"><input type="checkbox" checked=${chosen.includes(c.id)} onChange=${() => toggle(c.id)}/><span><b>${c.label}</b>${c.prompt && html`<small>${c.prompt.slice(0, 90)}</small>`}</span></label>`)}
    </fieldset>
    <button class="fx-go" type="button" onClick=${go} disabled=${busy || !chosen.length}>${busy ? "Checking" : chosen.length > 1 ? "Pick the best take" : "Check this take"}</button>
    ${err && html`<p class="fx-err" role="alert">${err}</p>`}
    ${res && html`<div role="status">${!res.single && html`<p><b>${res.picked ? "Picked: " + res.picked : "None picked"}</b> ${res.why}</p>`}
      <ul class="cp-results">${res.results.map((r) => html`<li key=${r.take}><${Verdict} v=${r.verdict}/> <b>${r.take}</b><span>${r.why}</span></li>`)}</ul></div>`}
  </section>`;
}

/* ---------- what ran here */
function Clip({ src, poster, label, children }) {
  return html`<figure class="cp-result"><video src=${src} poster=${poster || ""} controls playsinline loop muted preload="none" aria-label=${label}></video><figcaption><${AiMark}/> ${children}</figcaption></figure>`;
}

function Proof({ p }) {
  if (!p || !p.checked) return html`<section class="fx-card"><span class="fx-kick">Proof</span><h2>Nothing rendered here yet</h2><p class="small">Results appear here once they have run on this machine and been looked at.</p></section>`;
  const paths = Object.entries(p.wanpath || {}), hero = paths[0], rest = paths.slice(1), dir = Object.entries(p.director || {}), conf = p.confusion ? confusion(p.confusion.rows) : {};
  const nums = (r) => `${r.model}, seed ${r.seed}, ${r.seconds} s, peak ${r.peak_vram_gib} GiB.`;
  return html`<section class="fx-card cp-proof" aria-labelledby="cp-proof"><span class="fx-kick">Rendered on this machine and looked at, ${p.checked}</span><h2 id="cp-proof">Drawn moves, followed lines, checked takes</h2>
    ${hero && html`<div class="cp-hero"><${Clip} src=${hero[1].src} poster=${hero[1].poster} label=${"Drawn camera path: " + hero[0]}><${Verdict} v=${hero[1].verdict}/> <span><b>Drawn path.</b> ${hero[1].drawn_as}. The checker expected ${moveWord(hero[1].expect)}: ${hero[1].said}</span><small>${nums(hero[1])} ${hero[1].looked || ""}</small><//></div>`}
    <div class="fx-grid">
      ${rest.map(([k, r]) => html`<${Clip} key=${k} src=${r.src} poster=${r.poster} label=${"Drawn camera path: " + k}><${Verdict} v=${r.verdict}/> <span><b>Drawn path.</b> ${r.drawn_as}. Expected ${moveWord(r.expect)}: ${r.said}</span><small>${nums(r)} ${r.looked || ""}</small><//>`)}
      ${p.track && html`<${Clip} src=${p.track.src} poster=${p.track.poster} label="An object following a drawn line"><span><b>Drawn line.</b> ${p.track.subject}: ${p.track.follow ? `it stayed ${p.track.follow.mean_px} px from the line on average (worst ${p.track.follow.max_px} px, ${(p.track.follow.mean_of_diagonal * 100).toFixed(1)}% of the frame diagonal)${p.track.follow.lost_at != null ? `, and the tracker lost it at frame ${p.track.follow.lost_at}` : ""}.` : "not followed."}${p.track.follow_by_colour ? ` Checked by its colour instead: ${p.track.follow_by_colour.mean_px} px on average.` : ""}</span><small>${nums(p.track)} ${p.track.looked || ""}</small><a class="btn small" href=${p.track.guide} target="_blank" rel="noopener">Open the guide the LoRA saw</a><//>`}
    </div>
    ${dir.length > 0 && html`<h3>The checker on fresh takes</h3><div class="fx-grid">${dir.map(([mv, r]) => html`<${Clip} key=${mv} src=${r.src} poster=${r.poster} label=${"Take asked to " + moveWord(mv)}>${r.verdict && html`<${Verdict} v=${r.verdict}/>`} <span>Asked for <b>${moveWord(mv)}</b>.</span><small>${nums(r)} ${r.looked || ""}</small><//>`)}</div>`}
    ${p.pick && html`<h3>Picking the take that followed the move</h3><p>${p.pick.picked ? html`<b>Picked ${p.pick.picked}.</b> ` : html`<b>None picked.</b> `}${p.pick.why}</p>
      <div class="fx-grid">${(p.pick.takes || []).map((t) => { const r = (p.pick.results || []).find((x) => x.take === t.take) || {}; return html`<${Clip} key=${t.take} src=${t.src} poster=${t.poster} label=${t.take}>${r.verdict && html`<${Verdict} v=${r.verdict}/>`} <span><b>${t.take}${p.pick.picked === t.take ? " (picked)" : ""}</b> ${r.why || ""}</span><small>Seed ${t.seed}, ${t.seconds} s, peak ${t.peak_vram_gib} GiB.</small><//>`; })}</div>`}
    ${p.confusion && html`<details class="cp-tech"><summary>Every clip the checker was tested on</summary>
      <p class="small">Each clip was made here with a known requested move, including earlier showcase renders. The rules were written before any of them was measured and were not changed after. Not enough to tell is never a pass.</p>
      <table class="fx-table cp-conf"><thead><tr><th>Asked for</th><th>Match</th><th>Mismatch</th><th>Not enough to tell</th></tr></thead>
        <tbody>${Object.entries(conf).map(([m, c]) => html`<tr key=${m}><td>${moveWord(m)}</td><td>${c.MATCH}</td><td>${c.MISMATCH}</td><td>${c.INCONCLUSIVE}</td></tr>`)}</tbody></table>
      <ul class="cp-results">${p.confusion.rows.map((r) => html`<li key=${r.clip}><${Verdict} v=${r.verdict}/> <b>${r.clip}</b> asked ${moveWord(r.requested)}<span>${r.why}${r.eye ? " By eye: " + r.eye : ""}</span></li>`)}</ul></details>`}
    ${(p.faults || []).length > 0 && html`<div class="fx-note warn"><b>Faults seen</b><ul>${p.faults.map((f, i) => html`<li key=${i}>${f}</li>`)}</ul></div>`}
    ${(p.edits || []).length > 0 && html`<p class="small">Edits to inputs: ${p.edits.join(" ")}</p>`}
  </section>`;
}

export function CameraPaths() {
  const [info, setInfo] = useState(null), [err, setErr] = useState("");
  const load = () => { setErr(""); api("/api/campath").then(setInfo).catch((e) => setErr(said(e))); };
  useEffect(load, []);
  if (err) return html`<div class="fx"><div class="fx-note bad" role="alert"><p>${err}</p></div><button class="btn" onClick=${load}>Try again</button></div>`;
  if (!info) return html`<div class="fx"><${FxSkeleton} label="Reading the camera paths."/></div>`;
  return html`<div class="fx cp">
    <${Proof} p=${info.proof}/>
    <div class="fx-two"><${DrawMove} info=${info}/><${DrawLine} info=${info}/></div>
    <${Check} info=${info}/>
  </div>`;
}
