// The Game Builder page: prompts, a live stage board, the game itself in a frame, and the downloads. Every model, seed and licence on it is the one recorded by the build.
import { useEffect, useRef, useState } from "preact/hooks";
import { html, api, post } from "./common.js";
import { said } from "./fx.js";
import { STATUS_WORD, bytes, clock, progress, cleanPrompts, whyNot, endWord, standIns } from "./gamebuilder_logic.js";

const EXAMPLES = [
  ["A platformer in a glowing mushroom forest.", "You play as a cheerful forest ranger collecting golden acorns while avoiding grumpy walking pinecones."],
  ["Kart racing through a sunset desert canyon.", "Drive a stubby go-kart with chunky wheels. Called Canyon Dash."],
  ["A detective mystery in an old harbour town.", "Someone has stolen the harbour bell. Three people were there. One of them is lying."],
];
const Tag = ({ status }) => html`<span class=${"gb-tag " + status}>${STATUS_WORD[status] || status}</span>`;

/* The game in a frame. Nothing loads until asked: a build is tens of megabytes. */
function Player({ src, title, poster }) {
  const [on, setOn] = useState(false); const box = useRef(null);
  const full = () => { const f = box.current && box.current.querySelector("iframe"); if (f && f.requestFullscreen) f.requestFullscreen(); };
  useEffect(() => setOn(false), [src]);
  return html`<div class="gb-player" ref=${box}>
    ${on ? html`<iframe src=${src} title=${"Play " + title} allow="fullscreen; autoplay; gamepad" allowfullscreen></iframe>`
      : html`<button class="gb-start" type="button" onClick=${() => setOn(true)} style=${poster ? { backgroundImage: `url(${poster})` } : null}><span class="gb-startword">Play</span><span class="gb-startname">${title}</span></button>`}
    <div class="gb-under"><span class="small">Keyboard and mouse. Click in the game to steer with the mouse, and press Esc to get the mouse back.</span>${on && html`<button class="btn small" type="button" onClick=${full}>Full screen</button>`}</div>
    <p class="small gb-phone">These games are made for a keyboard. On a phone you can watch the play-test, but you can't really play.</p>
  </div>`;
}

function Stage({ s }) {
  const running = s.status === "running";
  return html`<li class=${"gb-stage " + s.status} aria-current=${running ? "step" : null}>
    <div class="gb-stagehead"><b>${s.label}</b><span class="gb-stagemeta">${s.seconds ? clock(s.seconds) + " " : ""}<${Tag} status=${s.status}/></span></div>
    ${s.items.length > 0 && html`<ul class="gb-items">${s.items.map((i) => html`<li key=${i.id} class=${"gb-item " + i.status}>
      <div class="gb-itemhead"><span>${i.what}</span><${Tag} status=${i.status}/></div>
      <dl class="gb-facts">${i.model && html`<div><dt>Made by</dt><dd>${i.model}${i.cached ? " (kept from an earlier run)" : ""}</dd></div>`}${i.seed != null && html`<div><dt>Seed</dt><dd>${i.seed}</dd></div>`}${i.seconds > 0 && html`<div><dt>Time</dt><dd>${clock(i.seconds)}</dd></div>`}${i.licence && html`<div class="wide"><dt>Licence</dt><dd>${i.licence}</dd></div>`}</dl>
      ${i.note && html`<p class="small gb-note">${i.note}</p>`}
    </li>`)}</ul>`}
  </li>`;
}

function Licences({ rows }) {
  if (!rows || !rows.length) return null;
  return html`<section class="gb-licence" aria-label="Licences"><h3>Before you ship this</h3><p>The game's assets keep the licence of the model that made them, and they go with the game wherever it goes. Read each one before you sell or publish it. The list is also in the game's Credits screen and <code>game/credits.json</code>.</p>
    <ul>${rows.map((r) => html`<li key=${r.licence}><b>${r.licence}</b><span class="small"> ${r.covers.join(", ")}</span></li>`)}</ul></section>`;
}

function Result({ g }) {
  const web = g.files && g.files.web; const pt = g.playtest || {};
  return html`<section class="gb-result" aria-label="The game"><span class="fx-kick">${endWord(g)}</span><h2>${g.title}</h2>
    <p class="small">${standIns(g.fallbacks)}${pt.result ? ` Play-test: ${pt.result} after ${clock(pt.played_s)} of play.` : ""}</p>
    ${web ? html`<${Player} src=${`/api/gamebuilder/games/${g.id}/web/index.html`} title=${g.title}/>` : html`<p class="fx-note warn">No web build was made, so it can't be played in this page.</p>`}
    <div class="fx-row">${["project", "linux", "web"].filter((k) => (g.sizes || {})[k + "_zip"]).map((k) => html`<a key=${k} class="btn" href=${`/api/gamebuilder/games/${g.id}/download/${k}`}>Download ${k === "project" ? "the Godot project" : k === "linux" ? "the Linux build" : "the web build"} (${bytes(g.sizes[k + "_zip"])})</a>`)}</div>
    ${g.has_video && html`<div><h3>The bot playing it</h3><video class="gb-video" controls preload="none" src=${`/api/gamebuilder/games/${g.id}/video`}></video></div>`}
    <${Licences} rows=${g.licence_summary}/>
  </section>`;
}

function Sample({ s }) {
  const media = s.playable ? html`<${Player} src=${s.src} title=${s.title} poster=${s.poster}/>` : html`<div class="gb-player"><video class="gb-video" controls preload="none" poster=${s.poster} src=${s.video} aria-label=${"The play-test bot playing " + s.title}></video><p class="small">The bot playing it. The playable build isn't on this machine: build it here from the same prompts.</p></div>`;
  return html`<article class="gb-sample">${media}
    <div class="gb-sampletext"><span class="fx-kick">${s.kit_label}</span><h3>${s.title}</h3><p class="small gb-prompts">${(s.prompts || []).join(" ")}</p>
    <dl class="gb-facts">${(s.made_by || []).map(([k, v]) => html`<div key=${k}><dt>${k}</dt><dd>${v}</dd></div>`)}</dl>
    ${s.notes && html`<p class="small">${s.notes}</p>`}${s.playable && s.video && html`<p class="small"><a href=${s.video}>Watch the bot play it</a></p>`}${s.licence_flag && html`<p class="small gb-flag">${s.licence_flag}</p>`}</div></article>`;
}

export function GameBuilder() {
  const [st, setSt] = useState(null), [prompts, setPrompts] = useState(["", ""]), [kit, setKit] = useState("auto"), [size, setSize] = useState("small"), [difficulty, setDifficulty] = useState("normal"), [seed, setSeed] = useState(""), [err, setErr] = useState(""), [plan, setPlan] = useState(null), [gid, setGid] = useState(""), [game, setGame] = useState(null), [busy, setBusy] = useState(false);
  const load = () => api("/api/gamebuilder/status").then(setSt).catch((e) => setErr(said(e)));
  useEffect(() => { load(); }, []);
  useEffect(() => {
    if (!gid) return undefined; let dead = false, timer = null;
    const tick = () => api(`/api/gamebuilder/games/${gid}`).then((g) => { if (dead) return; setGame(g); if (g.running) timer = setTimeout(tick, 2000); else load(); }).catch((e) => { if (!dead) setErr(said(e)); });
    tick(); return () => { dead = true; clearTimeout(timer); };
  }, [gid]);
  const r = st && st.readiness; const running = game && game.running;
  const blocked = whyNot(prompts, running, r);
  const body = () => ({ prompts: cleanPrompts(prompts), kit, size, difficulty, seed });
  const doPlan = () => { setErr(""); setBusy(true); post("/api/gamebuilder/plan", body()).then(setPlan).catch((e) => setErr(said(e))).finally(() => setBusy(false)); };
  const doBuild = () => { setErr(""); setBusy(true); post("/api/gamebuilder/games", body()).then((x) => { setGid(x.id); setGame(null); }).catch((e) => setErr(said(e))).finally(() => setBusy(false)); };
  const pr = game ? progress(game.stages) : null;
  return html`<div class="fx gb">
    ${st && st.samples.length > 0 && html`<section class="gb-samples" aria-label="Play a game made here"><h2>Play one made here</h2><p class="small gb-lede">Each of these came from the prompts printed under it, on our one GPU, with no hand edits. A bot played each to the win; the notes say what a clumsier bot managed.</p>${st.samples.map((s) => html`<${Sample} key=${s.id} s=${s}/>`)}</section>`}

    <section class="fx-card gb-form" aria-label="Your game"><h2>Your game</h2>
      ${prompts.map((p, i) => html`<label key=${i} class="fx-lab">${i === 0 ? "What's the game?" : "Anything else?"}<textarea class="fx-in gb-in" rows="2" value=${p} onInput=${(e) => { const n = [...prompts]; n[i] = e.target.value; setPrompts(n); }} placeholder=${EXAMPLES[0][i] || ""}></textarea></label>`)}
      <div class="fx-row">${prompts.length < 5 && html`<button class="btn small" type="button" onClick=${() => setPrompts([...prompts, ""])}>Add a prompt</button>`}${EXAMPLES.map((e, i) => html`<button key=${i} class="btn small" type="button" onClick=${() => setPrompts([...e])}>Example ${i + 1}</button>`)}</div>
      <div class="gb-opts"><label class="fx-lab">Genre kit<select class="fx-in" value=${kit} onChange=${(e) => setKit(e.target.value)}><option value="auto">Let the words decide</option>${(st ? st.kits : []).map((k) => html`<option key=${k.id} value=${k.id}>${k.label}</option>`)}</select></label>
        <label class="fx-lab">Size<select class="fx-in" value=${size} onChange=${(e) => setSize(e.target.value)}><option>small</option><option>medium</option><option>large</option></select></label>
        <label class="fx-lab">Difficulty<select class="fx-in" value=${difficulty} onChange=${(e) => setDifficulty(e.target.value)}><option>easy</option><option>normal</option><option>hard</option></select></label>
        <label class="fx-lab">Seed (optional)<input class="fx-in" inputmode="numeric" value=${seed} onInput=${(e) => setSeed(e.target.value)}/></label></div>
      <div class="fx-row"><button class="fx-go" type="button" disabled=${!!blocked || busy} onClick=${doBuild}>Build the game</button><button class="btn" type="button" disabled=${!!blocked || busy} onClick=${doPlan}>Show the spec first</button>${running && html`<button class="btn" type="button" onClick=${() => post(`/api/gamebuilder/games/${gid}/cancel`, {})}>Cancel</button>`}</div>
      ${blocked && html`<p class="small" role="status">${blocked}</p>`}
      ${err && html`<div class="fx-note bad" role="alert"><p>${err}</p></div>`}
      <ul class="gb-kits">${(st ? st.kits : []).map((k) => html`<li key=${k.id}><b>${k.label}</b> <span class="small">${k.pitch}</span></li>`)}</ul>
    </section>

    ${plan && html`<section class="fx-card" aria-label="The spec"><h2>The spec</h2><p class="small">${plan.note} ${plan.source === "words" ? "No model wrote this: it comes from your own words and a table of settings." : ""}</p><p><b>${plan.spec.title}</b>: ${plan.spec.tagline}</p><details><summary>All of it</summary><pre class="fx-pre">${JSON.stringify(plan.spec, null, 1)}</pre></details></section>`}

    ${game && html`<section class="gb-board" aria-label="The build"><div class="gb-boardhead"><h2>${game.title || "Starting"}</h2><p class="small" role="status">${endWord(game)}${pr ? `, ${pr.done} of ${pr.all} stages` : ""}${game.spec_source === "words" ? ". Spec from your words, no model." : ""}</p><div class="gb-bar" role="progressbar" aria-valuenow=${pr ? pr.pct : 0} aria-valuemin="0" aria-valuemax="100" aria-label="Stages finished"><i style=${{ width: (pr ? pr.pct : 0) + "%" }}></i></div></div>
      ${game.interrupted && html`<div class="fx-note warn"><p>This build stopped when the studio restarted. Press Build again with the same prompts and seed: what was finished comes from the cache.</p></div>`}
      ${game.error && html`<div class="fx-note bad" role="alert"><p>${game.error}</p></div>`}
      <ol class="gb-stages">${game.stages.map((s) => html`<${Stage} key=${s.id} s=${s}/>`)}</ol></section>`}
    ${game && (game.state === "done" || (game.files && game.files.web)) && html`<${Result} g=${game}/>`}

    ${st && st.games.length > 0 && html`<section class="fx-card" aria-label="Games made here"><h2>Games made here</h2><ul class="gb-past">${st.games.map((g) => html`<li key=${g.id}><button class="btn small" type="button" onClick=${() => setGid(g.id)}>Open</button> <b>${g.title || g.id}</b> <span class="small">${g.kit} · ${g.state}${g.result ? ` · bot ${g.result}` : ""}${g.fallbacks ? ` · ${g.fallbacks} stand-ins` : ""}</span></li>`)}</ul></section>`}

    ${r && html`<section class="fx-card" aria-label="This machine"><h2>This machine</h2><p class="small">${r.note} The models take turns, so the most the card holds for a build is about ${r.peak_gib} GiB. <a href="#fit">Hardware Fit</a> checks your card.</p>
      <ul class="gb-ready"><li class=${r.godot ? "ok" : "no"}><b>Godot ${r.godot_version}</b> <span class="small">${r.godot ? "Ready" : "Not found: set STUDIO_GODOT"}</span></li><li class=${r.templates ? "ok" : "no"}><b>Export templates</b> <span class="small">${r.templates ? "Ready" : "Missing: the game stays a project until they're installed"}</span>${!r.templates && html` <button class="btn small" type="button" onClick=${() => post("/api/gamebuilder/templates", { confirm: true }).then(load).catch((e) => setErr(said(e)))}>Fetch from Godot's release (over 1 GB, hash checked)</button>`}</li><li class=${r.comfy ? "ok" : "no"}><b>ComfyUI</b> <span class="small">${r.comfy ? "Answering" : "Not reachable: everything it makes becomes a stand-in"}</span></li>
      ${r.models.map((m) => html`<li key=${m.label} class=${m.ready ? "ok" : "no"}><b>${m.label}</b> <span class="small">${m.model}${m.peak_gib ? `, about ${m.peak_gib} GiB` : ""}. ${m.ready ? "Ready" : m.why}</span></li>`)}</ul></section>`}
    ${!st && !err && html`<p class="small" role="status">Looking at what this machine has.</p>`}
  </div>`;
}
