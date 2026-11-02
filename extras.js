import { useState, useEffect, useRef } from "preact/hooks";
import { html, api, post } from "./common.js";
import { Face, familyLabel } from "./prime_ui.js";
import { GraphPanel } from "./apipage.js";
import { matches, sectionOf, tagOf, useAllGraphs } from "./graph_rows.js";
import { Empty, Head, Offline, Stage, Stats, Strip, useHealth } from "./look.js";

/* ---------- Crew: every specialist has a face and a voice. Click one to talk to them in the dock, where they answer only from their notes and show the exact quote ---------- */
function CrewCard({ m, state }) {
  const on = state.open && state.id === m.id, say = state.speaking === m.id;
  return html`<button class=${"ccard tilt3d" + (on ? " on" : "") + (say ? " speaking" : "")} onClick=${() => dispatchEvent(new CustomEvent("crew-talk", { detail: m }))} aria-label=${`Talk to ${m.name}, ${familyLabel(m)}`}>
    <${Face} member=${m} speaking=${say}/><span class="cshade"></span>${say ? html`<span class="cflag">Speaking</span>` : on ? html`<span class="cflag">Talking</span>` : null}
    <span class="ctext"><b>${m.name}</b><small>${familyLabel(m)}${m.tier !== "family" || m.has_dossier === true ? "" : " (no notes yet)"}</small></span></button>`;
}
export function Crew() {
  const [members, setMembers] = useState(null); const [q, setQ] = useState(""); const [err, setErr] = useState(""); const [state, setState] = useState({});
  useEffect(() => { api("/api/crew").then((d) => setMembers(d.members)).catch((e) => setErr(e.message)); const f = (e) => setState(e.detail); addEventListener("crew-state", f); return () => removeEventListener("crew-state", f); }, []);
  const ask = () => { if (q.trim().length < 3) return; dispatchEvent(new CustomEvent("crew-talk", { detail: { ask: q.trim() } })); setQ(""); };
  const tiers = ["studio", "family", "secondary", "tertiary"]; const label = { studio: "Studio specialists", family: "Model specialists", secondary: "Shared experts", tertiary: "Fine-tuning experts" };
  const prime = (members || []).find((m) => m.tier === "master"); const say = state.speaking === "master"; const [tier, setTier] = useState("all"); const inTier = (t) => (members || []).filter((m) => m.tier === t).length;
  return html`<div class="lk cr-page">${err && html`<p class="small" style="color:var(--err)" role="alert">${err}</p>`}
    <div class="crewtop">${prime && html`<button class=${"crewprime" + (say ? " speaking" : "")} onClick=${() => dispatchEvent(new CustomEvent("crew-talk", { detail: prime }))} aria-label="Talk to Comfy Prime"><${Face} member=${prime} speaking=${say}/><span class="ctext"><b>${prime.name}</b><small>Your guide. Holds every specialist's notes and learns your name.</small><em>Talk to me</em></span></button>`}
      <div class="crewask"><h2 class="cr-askh">Ask the crew</h2><p>Every model family and every part of the studio has a specialist who has read all our notes on it. Click a face to talk to them: they answer aloud, only from those notes, and show the exact quote so you can check them.</p>
        <div class="row" style="margin:0"><input type="text" placeholder="Or ask whoever knows best, e.g. how many steps should Klein use?" value=${q} onInput=${(e) => setQ(e.target.value)} onKeyDown=${(e) => e.key === "Enter" && ask()} aria-label="question for the crew"/><button class="btn primary" onClick=${ask} disabled=${q.trim().length < 3}>Ask</button></div></div></div>
    ${members && html`<${Strip} label="Which specialists" value=${tier} onPick=${setTier} items=${[{ k: "all", b: "Everyone", s: `${members.filter((m) => m.tier !== "master").length} specialists` }, ...tiers.filter((t) => inTier(t)).map((t) => ({ k: t, b: label[t], s: `${inTier(t)} on the crew` }))]}/>`}
    ${members && tiers.filter((t) => tier === "all" || tier === t).map((t) => { const l = members.filter((m) => m.tier === t); return l.length ? html`<div class="sect crewsect"><h2>${label[t]}</h2></div><div class="crewgrid">${l.map((m) => html`<${CrewCard} key=${m.id} m=${m} state=${state}/>`)}</div>` : null; })}
    ${!members && !err && html`<p class="small">Loading the crew...</p>`}</div>`;
}

/* ---------- Site builder ---------- */
const SITE_NOTE = "Six sample sites, built by this studio's page builder from invented briefs. We wrote their words by hand from each brief, because the local AI was asleep when we made them, and put our own renders in the picture slots. Press Build and the local AI writes yours.";
function SiteTile({ x, hidden }) {
  return html`<a class="sw-site" href=${`site_examples/${x.slug}/index.html`} target="_blank" rel="noopener noreferrer" tabindex=${hidden ? "-1" : undefined} aria-hidden=${hidden ? "true" : undefined}>
    <span class="sw-browser"><span class="sw-bar" aria-hidden="true"><i></i><i></i><i></i><u>${x.slug}</u></span><span class="sw-page"><img src=${`site_examples/${x.slug}_desktop.webp`} alt=${hidden ? "" : `The ${x.name} sample site on a desktop`} loading="lazy"/></span></span>
    <span class="sw-phone"><img src=${`site_examples/${x.slug}_phone.webp`} alt=${hidden ? "" : `The ${x.name} sample site on a phone`} loading="lazy"/></span>
    <span class="sw-cap"><b>${x.name}</b><small>${x.label}, sample. Opens the real pages.</small></span></a>`;
}
function SiteWipe({ sites }) {
  const [at, setAt] = useState(0), [pos, setPos] = useState(55); const x = sites[at] || sites[0];
  if (!x) return null;
  return html`<div class="sw-wipe film"><div class="sw-wipestage" style=${{ "--pos": pos + "%" }}>
      <div class="sw-brief"><span class="lk-tag">The brief</span><h3>${x.name}</h3><dl><div><dt>Voice</dt><dd>${x.voice}</dd></div><div><dt>Colour</dt><dd><i style=${{ background: x.brand }}></i>${x.brand}</dd></div><div><dt>Pages</dt><dd>${x.pages}</dd></div>${Object.entries(x.facts).map(([k, v]) => html`<div key=${k}><dt>${k}</dt><dd>${v}</dd></div>`)}</dl></div>
      <div class="sw-after"><img src=${`site_examples/${x.slug}_desktop.webp`} alt=${`The finished ${x.name} site`}/><span class="lk-tag">The site</span></div>
      <span class="sw-line" aria-hidden="true"></span><input type="range" min="0" max="100" value=${pos} onInput=${(e) => setPos(+e.target.value)} aria-label="Wipe from the brief to the finished site"/></div>
    <div class="sw-wipeside"><ul class="lk-rack">${sites.map((y, i) => html`<li key=${y.slug}><button type="button" aria-pressed=${i === at} onClick=${() => setAt(i)}><img src=${`site_examples/${y.slug}_desktop.webp`} alt="" loading="lazy"/><span><b>${y.name}</b><small>${y.label}</small></span></button></li>`)}</ul><a class="btn primary sw-open" href=${`site_examples/${x.slug}/index.html`} target="_blank" rel="noopener noreferrer">Open ${x.name}</a></div></div>`;
}
export function Site() {
  const [name, setName] = useState(""); const [brand, setBrand] = useState(""); const [colour, setColour] = useState("#b5651d"); const [pages, setPages] = useState("home, about, contact"); const [facts, setFacts] = useState([["", ""], ["", ""], ["", ""]]); const [busy, setBusy] = useState(false); const [err, setErr] = useState(""); const [site, setSite] = useState(null);
  const [sites, setSites] = useState([]), [doc, setDoc] = useState(""), [wide, setWide] = useState(true), [warn, setWarn] = useState("");
  useEffect(() => { fetch("site_examples/index.json").then((r) => (r.ok ? r.json() : [])).then(setSites).catch(() => {}); }, []);
  const brief = () => ({ name, voice: brand, brand: colour, pages: pages.split(",").map((x) => x.trim()).filter(Boolean), facts: Object.fromEntries(facts.filter(([k, v]) => k.trim() && v.trim())) });
  useEffect(() => { const t = setTimeout(() => post("/api/site/preview", { brief: brief() }).then((r) => { setDoc(r.html); setWarn(""); }).catch((e) => setWarn(e.message)), 180); return () => clearTimeout(t); }, [name, brand, colour, pages, JSON.stringify(facts)]);
  const go = async () => {
    setBusy(true); setErr(""); setSite(null);
    try { const r = await post("/api/site/build", { brief: brief() }); if ((r.files || []).length && !(r.problems || []).length) setSite(r); else setErr((r.problems || []).join("; ") || "The site could not be built."); } catch (e) { setErr(e.message); }
    setBusy(false);
  };
  const fill = (x) => { setName(x.name); setBrand(x.voice); setColour(x.brand); setPages(x.pages); setFacts(Object.entries(x.facts).slice(0, 3)); document.getElementById("st-b")?.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" }); };
  const rows = [sites.filter((_, i) => i % 2 === 0), sites.filter((_, i) => i % 2 === 1)];
  return html`<div class="lk st-page">
    <p class="lk-plain">Describe a small business or project and the studio writes and builds a clean, accessible, safe-for-work website from your facts only. It never invents details. A local AI writes the pages, the studio builds them, and you keep clean files to host anywhere. Open it, or hand it to your editor.</p>
    ${sites.length > 0 && html`<section class="sw-wall film" aria-label="Sample sites"><div class="sw-rows">${rows.map((row, r) => html`<div class=${"sw-row" + (r ? " rev" : "")} key=${r}><div class="sw-track">${row.map((x) => html`<${SiteTile} key=${x.slug} x=${x}/>`)}${row.map((x) => html`<${SiteTile} key=${x.slug + "b"} x=${x} hidden/>`)}</div></div>`)}</div><p class="lk-stagenote">${SITE_NOTE}</p></section>`}
    ${sites.length > 0 && html`<section aria-labelledby="st-w"><${Head} n=${1} id="st-w" sub="Drag across, or use the arrow keys. Left is what went in, right is what came out.">A brief in. A site out.<//><${SiteWipe} sites=${sites}/></section>`}
    <section aria-labelledby="st-ex"><${Head} n=${2} id="st-ex" sub="Each one fills in the form below, and nothing runs until you press Build.">Start from one of these<//>
      <div class="chips st-fills">${sites.map((x) => html`<button key=${x.slug} type="button" class="chip" onClick=${() => fill(x)}>${x.label}</button>`)}</div></section>
    <div class="st-work">
      <section class="card st-brief" aria-labelledby="st-b"><${Head} n=${3} id="st-b">Your brief<//>
        <label class="lk-field">Name (required)<input type="text" value=${name} onInput=${(e) => setName(e.target.value)}/></label>
        <div class="st-pair"><label class="lk-field">Brand voice<input type="text" placeholder="e.g. warm, playful, precise" value=${brand} onInput=${(e) => setBrand(e.target.value)}/></label><label class="lk-field st-colour">Colour<input type="color" value=${colour} onInput=${(e) => setColour(e.target.value)}/></label></div>
        <label class="lk-field">Pages (comma separated)<input type="text" value=${pages} onInput=${(e) => setPages(e.target.value)}/></label>
        <h3>Facts the copy may use</h3>
        ${facts.map((p, i) => html`<div class="st-fact"><input type="text" placeholder="e.g. hours" value=${p[0]} onInput=${(e) => setFacts(facts.map((x, j) => (j === i ? [e.target.value, x[1]] : x)))} aria-label=${`Fact ${i + 1} name`}/><input type="text" placeholder="e.g. Mon-Fri 9 to 5" value=${p[1]} onInput=${(e) => setFacts(facts.map((x, j) => (j === i ? [x[0], e.target.value] : x)))} aria-label=${`Fact ${i + 1} text`}/></div>`)}
        <button class="btn primary st-go" disabled=${busy || !name.trim()} onClick=${go}>${busy ? "Building..." : "Build the site"}</button><p class="small st-needs">Build needs the local AI running, to write the words. The preview does not.</p>${err && html`<p class="small" style="color:var(--err)" role="alert">${err}</p>`}</section>
      <section class="card st-preview" aria-labelledby="st-p"><${Head} n=${4} id="st-p">${site ? "Your site" : "Assembling as you type"}<//>
        ${site ? html`<div class="st-frameb"><span class="sw-bar" aria-hidden="true"><i></i><i></i><i></i><u>${name}</u></span><iframe title="site preview" sandbox="" src=${`/api/site/${site.site_id}/index.html`} class="st-frame"></iframe></div><div class="row"><a class="btn small" target="_blank" rel="noopener noreferrer" href=${`/api/site/${site.site_id}/index.html`}>Open in a tab</a><span class="small">${(site.files || []).length} files</span></div>` : html`<div class="st-seg" role="group" aria-label="Preview size"><button type="button" class=${"chip" + (wide ? " on" : "")} aria-pressed=${wide} onClick=${() => setWide(true)}>Desktop</button><button type="button" class=${"chip" + (!wide ? " on" : "")} aria-pressed=${!wide} onClick=${() => setWide(false)}>Phone</button></div>
          <div class=${"st-frameb" + (wide ? "" : " narrow")}><span class="sw-bar" aria-hidden="true"><i></i><i></i><i></i><u>${name || "your site"}</u></span><iframe title="preview of your brief" sandbox="" srcdoc=${doc} class="st-frame"></iframe></div>${warn ? html`<p class="small" style="color:var(--err)" role="alert">${warn}</p>` : html`<p class="small">A preview of your name, pages, facts and colour, with the builder's real styles. Nothing has been written or saved yet.</p>`}`}</section>
    </div></div>`;
}

/* ---------- 3D ---------- */
export { Studio3D } from "./studio3d.js";

/* ---------- Edit: a real multi-track timeline over your own results ---------- */
import { Timeline } from "./timeline_ui.js";
export function Edit() {
  const health = useHealth(); const [lib, setLib] = useState(null); const [rendering, setRendering] = useState(false); const [out, setOut] = useState(null); const [err, setErr] = useState("");
  useEffect(() => {
    (async () => {
      try {
        const hist = await api("/api/history?limit=60&only=main"); const items = [];
        for (const e of hist) for (const f of e.files) {
          if (f.kind === "image") continue; const src = (f.subfolder ? f.subfolder + "/" : "") + f.filename;
          try { const p = await api("/api/probe?path=" + encodeURIComponent(src)); if (p.duration > 0) items.push({ src, label: (e.prompt || f.filename).slice(0, 28), kind: f.kind === "audio" ? "audio" : "video", dur: p.duration }); } catch {}
        }
        setLib(items);
      } catch (e) { setErr(e.message); setLib([]); }
    })();
  }, [health && health.comfy]);
  const render = async (edl) => {
    setRendering(true); setErr(""); setOut(null);
    try {
      const { render: rid } = await post("/api/timeline/render", { edl });
      for (let i = 0; i < 400; i++) { await new Promise((r) => setTimeout(r, 1500)); const s = await api("/api/timeline/render/" + rid); if (s.status === "done") { setOut(s); break; } if (s.status === "error") { setErr((s.problems || []).join("; ") || s.tail || "render failed"); break; } }
    } catch (e) { setErr(e.message); }
    setRendering(false);
  };
  return html`<div class="lk ed-timeline"><p class="lk-plain">Cut your generated clips together: add clips from your library, drag to move, drag the edges to trim, split at the playhead, then render one finished video. It runs on your machine with ffmpeg.</p>
    ${lib && !lib.length && html`<${Empty} art="edit_art/h3_extend.webp" kicker="The timeline" title=${health && !health.comfy ? "Your clips can't be listed" : "No clips yet"} note="The picture is our own render, not yours."><p>${health && !health.comfy ? "The list of finished clips comes from ComfyUI, and it is not reachable right now. Your files are not gone. Start ComfyUI and they come back on this page." : "Make a video or a song in Create and it shows up here to cut. The final cut runs on ffmpeg on this machine."}</p><div class="lk-acts"><a class="btn primary" href="#create">Go to Create</a><a class="btn" href="#library">Open the Library</a></div><//>`}
    ${lib === null ? html`<p class="small">Loading your clips...</p>` : html`<${Timeline} library=${lib} onRender=${render} rendering=${rendering}/>`}
    ${err && html`<p class="small" style="color:var(--err)">${err}</p>`}
    ${out && html`<div class="card" style="margin-top:14px"><h3>Rendered in ${out.seconds}s</h3><video src=${out.url} controls style="max-width:100%;border-radius:12px"></video><div class="row"><a class="btn small" href=${out.url} download>Download</a></div></div>`}</div>`;
}

/* ---------- Try-on and try-off, on the Fashion designer's page ---------- */
function TryOn() {
  const [d, setD] = useState(null), [dir, setDir] = useState("on"), [mid, setMid] = useState(""), [person, setPerson] = useState(""), [garment, setGarment] = useState(""), [cat, setCat] = useState("tops"), [job, setJob] = useState(null), [err, setErr] = useState("");
  useEffect(() => { api("/api/tryon/methods").then((x) => { setD(x); setMid(x.default.on || ""); }).catch((e) => setErr(e.message)); }, []);
  useEffect(() => { if (!job || job.status !== "running") return undefined; const t = setInterval(() => api("/api/tryon/jobs/" + job.job).then(setJob).catch((e) => setErr(e.message)), 2500); return () => clearInterval(t); }, [job && job.job, job && job.status]);
  if (!d) return err ? html`<p class="small" style="color:var(--err)">${err}</p>` : null;
  const rows = d.methods.filter((m) => m.direction === dir), m = rows.find((x) => x.id === mid), busy = job && job.status === "running", pick = (x) => { setDir(x); setMid(d.default[x] || ""); };
  const up = (set) => async (e) => { const f = e.target.files && e.target.files[0]; if (!f) return; const b = new FormData(); b.append("file", f); try { set((await api("/api/upload", { method: "POST", body: b })).name); } catch (x) { setErr(x.message); } };
  const go = async () => { setErr(""); try { setJob(await post("/api/tryon/run", { method: mid, person, garment, category: cat })); } catch (x) { setErr(x.message); } };
  const sel = "background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:10px;padding:8px;width:100%;max-width:100%;margin-top:3px";
  const file = (label, value, set) => html`<label class="de-file"><span>${label}</span><b>${value || "Choose a picture"}</b><input type="file" accept="image/png,image/jpeg,image/webp" aria-label=${label} onChange=${up(set)}/></label>`;
  return html`<section class="de-layout de-tryon" aria-label="Try-on and try-off"><div class="card"><h3>Try it on, or take it off</h3><p class="small" style="margin:0 0 10px">Use invented, adult people, fully clothed. There is no way to copy a real person's face here.</p>
    <div class="row" style="margin:0 0 10px"><button class=${"chip" + (dir === "on" ? " on" : "")} aria-pressed=${dir === "on"} onClick=${() => pick("on")}>Try-on</button><button class=${"chip" + (dir === "off" ? " on" : "")} aria-pressed=${dir === "off"} onClick=${() => pick("off")}>Try-off</button></div>
    <div class="row" style="margin:0 0 8px"><label class="small de-pick">Model <select style=${sel} value=${mid} onChange=${(e) => setMid(e.target.value)}>${rows.map((x) => html`<option key=${x.id} value=${x.id} disabled=${!x.ready}>${x.label}${x.id === d.default[dir] ? " (default)" : ""}${x.commercial ? "" : " (non-commercial)"}${x.ready ? "" : " (not ready)"}</option>`)}</select></label>
      ${m && m.id === "fashn" && html`<label class="small de-pick">Garment <select style=${sel} value=${cat} onChange=${(e) => setCat(e.target.value)}><option value="tops">Top</option><option value="bottoms">Bottoms</option><option value="one-pieces">One piece</option></select></label>`}</div>
    ${m && html`<p class="small" style="margin:0 0 10px">${m.note} Licence: ${m.licence}.${m.commercial ? "" : html` <b>Not for commercial use.</b>`}${m.ready ? "" : " " + m.why_not}</p>`}
    <div class="de-files">${file("The person", person, setPerson)}${dir === "on" && file("The garment", garment, setGarment)}</div>
    <div class="row"><span class="grow"></span><button class="btn primary" disabled=${!m || !m.ready || busy || !person || (dir === "on" && !garment)} onClick=${go}>${busy ? "Running..." : dir === "on" ? "Try it on" : "Take it off"}</button></div>
    ${job && job.status === "error" && html`<p class="small" style="color:var(--err)" role="alert">${job.error}</p>`}${err && html`<p class="small" style="color:var(--err)" role="alert">${err}</p>`}</div>
    <div class="card"><h3>Result</h3>${job && job.status === "done" ? html`<figure class="de-sample film"><img src=${"/api/view?filename=" + encodeURIComponent(job.file.split("/").pop()) + "&subfolder=tryon"} alt="The result"/><figcaption>${job.seconds} s, on your GPU. Saved in your output folder.</figcaption></figure>` : html`<figure class="de-sample film"><img src="families/flux-2_11.webp" alt="" loading="lazy" onError=${(e) => { e.target.closest("figure").style.display = "none"; }}/><figcaption>Our own test with FLUX.2 Klein 4B and an invented model, not yours.</figcaption></figure><p class="small" style="margin:0">${busy ? "Working. This takes one to two minutes." : "Your picture appears here."}</p>`}</div></section>`;
}

/* ---------- Designers: pick options from the owner's designer modules, render a sheet of views ---------- */
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function runJob(body) {
  const { job } = await post("/api/generate", body);
  for (let i = 0; i < 600; i++) { await sleep(1500); const s = await api("/api/jobs/" + job); if (s.status === "done") return s; if (s.status === "error") throw new Error(s.error || "the job failed"); }
  throw new Error("timed out");
}
/* one plain line per designer for its tile; the picture is a real render from the designer's own composer (scripts/build_designer_art.py) */
const DESIGNER_LINE = { character: "Original adult characters, headshots to full body", fashion: "Outfits, shoes and accessories as a sheet", tshirt: "Tees and sweats, print by print", mug: "Mugs with your own artwork", printify: "Art on print-on-demand products", vehicle: "Cars, bikes and wild builds", setting: "Rooms, places and moods", animal: "Any animal, in any light", plant: "Houseplants to whole gardens", hair: "Cuts, colours and textures", nail: "Nail shapes, finishes and art", furniture: "Furniture in any style", cosplay: "Original costumes, armour to props", sneaker: "Shoes from court classics to printed lattice", watch: "Dials, cases and movements", jewellery: "Rings, crowns and gems", perfume: "Bottles, glass and packaging", architecture: "Houses in impossible places", robot: "Machines from pocket-sized to skyscraper", spaceship: "Ships, hulls and engines", creature: "Original beasts in their habitats", helmet: "Helms and armour on the stand", album: "Cover art, with no type", poster: "Printed posters, with no type", stainedglass: "Windows lit from behind", textile: "Prints, weaves and rugs", flash: "Bold ink designs on paper", cake: "Showpiece cakes and what is inside", stage: "Sets for opera, concerts and ballet", lamp: "Lamps lit in the dark", gameprop: "Swords, chests and potions", toy: "Tin, wood and felt" };
function PrintifyCard() {
  const [p, setP] = useState(null); const [tok, setTok] = useState(""); const [err, setErr] = useState("");
  useEffect(() => { api("/api/printify").then(setP).catch(() => {}); }, []);
  if (!p) return null;
  const go = async () => { setErr(""); try { setP(await post("/api/printify/connect", { token: tok })); setTok(""); } catch (e) { setErr(e.message); } };
  return html`<div class="card" style="margin:0 0 14px"><h3>Connect your Printify</h3>${p.connected ? html`<p class="small">Connected: ${p.shops.map((s) => s.title).join(", ") || "no shops yet"}. Finished products can go to your shop as drafts; nothing is published.</p>` : html`<p class="small">Paste a Printify personal access token to send designs to your own shop as drafts. It stays on this computer.</p><div class="row"><input type="text" placeholder="Printify token" value=${tok} onInput=${(e) => setTok(e.target.value)} aria-label="Printify token" style="max-width:420px"/><button class="btn small primary" disabled=${!tok.trim()} onClick=${go}>Connect</button></div>`}${err && html`<p class="small" style="color:var(--err)">${err}</p>`}</div>`;
}
/* The reel: real renders only. Each designer's tile, plus other views and single-choice changes made with the same seed by its own composer (scripts/build_designer_sheets.py). */
const framesOf = (id, rec, sheets) => { const rows = sheets.filter((x) => x.id === id), base = rec ? [{ key: "base", src: `designer_art/${id}.webp`, label: rec.view, kind: "base", prompt: rec.prompt, seed: rec.seed, model: rec.model, seconds: rec.seconds, peak_vram_gib: rec.peak_vram_gib, made: rec.made }] : []; return [...base, ...rows.map((x) => ({ ...x, key: x.file, src: x.file }))]; };
function DesignReel({ list, open }) {
  const [art, setArt] = useState([]), [sheets, setSheets] = useState([]), [at, setAt] = useState(0), [pick, setPick] = useState(0), [count, setCount] = useState({}); const reel = useRef(null);
  useEffect(() => { fetch("designer_art/art.json").then((r) => (r.ok ? r.json() : [])).then(setArt).catch(() => {}); fetch("designer_art/sheets.json").then((r) => (r.ok ? r.json() : [])).then(setSheets).catch(() => {}); }, []);
  const rows = list.map((p) => ({ ...p, art: art.find((a) => a.id === p.id) })).filter((p) => !art.length || p.art), cur = rows[Math.min(at, rows.length - 1)];
  useEffect(() => { const el = reel.current; if (!el || !rows.length) return; const io = new IntersectionObserver((es) => { const v = es.filter((e) => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0]; if (v) { setAt(+v.target.dataset.i); setPick(0); } }, { root: el, threshold: [0.55, 0.8] }); el.querySelectorAll(".de-sheet").forEach((x) => io.observe(x)); return () => io.disconnect(); }, [rows.length]);
  const go = (i) => { const el = reel.current, n = el && el.querySelector(`[data-i="${Math.max(0, Math.min(rows.length - 1, i))}"]`); if (n) { n.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", inline: "center", block: "nearest" }); setAt(+n.dataset.i); setPick(0); } };
  if (!cur) return html`<p class="small">Loading the designers...</p>`;
  const frames = framesOf(cur.id, cur.art, sheets), frame = frames[Math.min(pick, frames.length - 1)], views = frames.filter((x) => x.kind !== "choice"), morphs = frames.filter((x) => x.kind === "choice"), group = morphs[0] && morphs[0].group, baseValue = group && cur.art && cur.art.choices[group];
  const scrub = (e) => { if (e.pointerType !== "mouse" || views.length < 2) return; const r = e.currentTarget.getBoundingClientRect(), k = Math.min(views.length - 1, Math.floor(((e.clientX - r.left) / r.width) * views.length)), f = frames.indexOf(views[k]); if (f !== pick) setPick(f); };
  return html`<section class="de-stage film" aria-label="Designers">
    <div class="de-glow" aria-hidden="true">${rows.map((r, i) => html`<img key=${r.id} class=${i === at ? "on" : ""} src=${`designer_art/${r.id}.webp`} alt="" loading="lazy" onError=${(e) => { e.target.remove(); }}/>`)}</div>
    <div class="de-reel" ref=${reel} tabindex="0" role="group" aria-label="Designers, one at a time. Scroll sideways to move." onKeyDown=${(e) => { if (e.target !== e.currentTarget) return; if (e.key === "ArrowRight") { e.preventDefault(); go(at + 1); } if (e.key === "ArrowLeft") { e.preventDefault(); go(at - 1); } }}>
      ${rows.map((r, i) => html`<button key=${r.id} type="button" class=${"de-sheet" + (i === at ? " on" : "")} data-i=${i} aria-label=${i === at ? `Open ${r.label}` : `Show ${r.label}`} aria-current=${i === at ? "true" : undefined} onPointerMove=${i === at ? scrub : undefined} onClick=${() => (i === at ? open(r.id) : go(i))}><img src=${`designer_art/${r.id}.webp`} alt="" loading=${i < 3 ? "eager" : "lazy"} onError=${(e) => { e.target.style.visibility = "hidden"; }}/>
        ${i === at && frame && frame.kind !== "base" && html`<img key=${frame.key} class="de-morph" src=${frame.src} alt=""/>`}${i === at && frame && html`<span class="de-frame"><b>${frame.kind === "choice" ? `${frame.group_label}: ${frame.label}` : frame.label}</b></span>`}</button>`)}</div>
    <ul class="de-film" aria-label="Jump to a designer">${rows.map((r, i) => html`<li key=${r.id}><button type="button" aria-pressed=${i === at} aria-label=${r.label} onClick=${() => go(i)}><img src=${`designer_art/${r.id}.webp`} alt="" loading="lazy"/></button></li>`)}</ul>
    <div class="de-ctl"><button type="button" class="de-arrow" disabled=${at === 0} onClick=${() => go(at - 1)} aria-label="Previous designer">←</button><span class="de-pos" aria-live="polite">${at + 1} of ${rows.length}</span><button type="button" class="de-arrow" disabled=${at === rows.length - 1} onClick=${() => go(at + 1)} aria-label="Next designer">→</button></div>
    <div class="de-info">
      <div class="de-head"><span class="lk-tag">Our renders</span><h2>${cur.label}</h2><p>${DESIGNER_LINE[cur.id] || "A full sheet of views"}</p><div class="lk-acts"><button type="button" class="btn primary" onClick=${() => open(cur.id)}>Open ${cur.label}</button></div></div>
      <${Stats} items=${[[cur.views, "views in a sheet"], [cur.groups, "groups of choices"]]}/>
      ${views.length > 1 && html`<div class="de-slots"><h3>The sheet</h3><ol>${views.map((v) => html`<li key=${v.key}><button type="button" aria-pressed=${v === frame} onClick=${() => setPick(frames.indexOf(v))}><img src=${v.src} alt="" loading="lazy"/><small>${v.label}</small></button></li>`)}</ol>${cur.views > views.length && html`<p class="small">${cur.views - views.length} more views can be made in the designer.<span class="de-hint"> Move across the picture to flip through these.</span></p>`}</div>`}
      ${morphs.length > 0 && html`<div class="de-slots de-morphs"><h3>Change one choice: ${morphs[0].group_label}</h3><div class="chips">${baseValue && html`<button type="button" class=${"chip" + (frame.kind === "base" ? " on" : "")} aria-pressed=${frame.kind === "base"} onClick=${() => setPick(0)}>${baseValue}</button>`}${morphs.map((m) => html`<button key=${m.key} type="button" class=${"chip" + (m === frame ? " on" : "")} aria-pressed=${m === frame} onClick=${() => setPick(frames.indexOf(m))}>${m.label}</button>`)}</div><p class="small">Same seed and same words, with only this choice changed. Each one is a separate render.</p></div>`}
      ${frame && html`<details class="de-how"><summary>How this picture was made</summary><p>${frame.prompt}</p><p class="small">${frame.model}. Seed ${frame.seed}.${frame.seconds ? ` ${frame.seconds} s` : ""}${frame.peak_vram_gib ? `, ${frame.peak_vram_gib} GB peak VRAM` : ""}${frame.made ? `, on ${frame.made}` : ""}.</p></details>`}
    </div></section>`;
}
export function Designers({ route, health }) {
  const [list, setList] = useState([]); const [pack, setPack] = useState(null); const packId = (route || "").split("/")[1] || ""; const [goals, setGoals] = useState({}); const [goal, setGoal] = useState("image");
  const [choices, setChoices] = useState({}); const [idea, setIdea] = useState(""); const [words, setWords] = useState(""); const [views, setViews] = useState([]); const [results, setResults] = useState([]); const [busy, setBusy] = useState(false); const [err, setErr] = useState("");
  useEffect(() => { api("/api/packs").then((d) => { setList(d.packs); let w = null; try { w = sessionStorage.getItem("designer_open"); sessionStorage.removeItem("designer_open"); } catch {} if (w) open(w); }).catch((e) => setErr(e.message)); api("/api/goals").then(setGoals).catch(() => {}); }, []);
  const open = (id) => { location.hash = "design/" + id; };
  useEffect(() => { if (!packId) { setPack(null); return; } let on = true; api("/api/packs/" + packId).then((p) => { if (on) { setPack(p); setChoices({}); setResults([]); setViews(p.views.slice(0, 3)); setErr(""); } }).catch((e) => { if (on) setErr(e.message); }); return () => { on = false; }; }, [packId]);
  const engines = Object.values(goals).filter((g) => g.kind === "image" && !g.needs_image);
  const make = async () => {
    setBusy(true); setErr(""); setResults([]); const vs = views.length ? views : [""];
    try {
      for (const v of vs) {
        const { prompt } = await post(`/api/packs/${pack.id}/compose`, { choices, idea, view: v, words });
        const slot = { view: v, prompt, files: null }; setResults((r) => [...r, slot]);
        try { const s = await runJob({ goal, prompt, options: {} }); slot.files = s.files; } catch (e) { slot.error = e.message; }
        setResults((r) => r.map((x) => (x === slot ? { ...slot } : x)));
      }
    } catch (e) { setErr(e.message); }
    setBusy(false);
  };
  const toggle = (v) => setViews(views.includes(v) ? views.filter((x) => x !== v) : [...views, v]);
  const [promptText, setPromptText] = useState(""), [examples, setExamples] = useState([]);
  useEffect(() => { fetch("designer_art/sheets.json").then((r) => (r.ok ? r.json() : [])).then(setExamples).catch(() => {}); }, []);
  /* the picture beside the form follows your picks when we have a real render of that choice or view. It never pretends to be your result. */
  const sampleFor = () => { const own = examples.filter((x) => pack && x.id === pack.id), c = own.find((x) => x.kind === "choice" && choices[x.group] === x.label), v = own.find((x) => x.kind === "view" && views[0] === x.label); if (c) return { src: c.file, note: `Our own render with ${c.group_label.toLowerCase()} set to ${c.label}, not yours. Only that choice differs from our first picture.` }; if (v) return { src: v.file, note: `Our own render of this view, with our choices, not yours.` }; return { src: pack ? `designer_art/${pack.id}.webp` : "", note: "Our own render from this designer, with our choices, not yours." }; };
  const sample = sampleFor();
  useEffect(() => { if (!pack) return; let on = true; const t = setTimeout(() => post(`/api/packs/${pack.id}/compose`, { choices, idea, view: views[0] || "", words }).then((r) => { if (on) setPromptText(r.prompt); }).catch((e) => { if (on) setPromptText(e.message); }), 160); return () => { on = false; clearTimeout(t); }; }, [pack && pack.id, JSON.stringify(choices), idea, words, views[0]]);
  if (!pack || !packId) return html`<div class="lk de-page">${health && health.edition === "extended" && html`<${PrintifyCard}/>`}
    ${err && html`<p class="small" style="color:var(--err)" role="alert">${err}</p>`}<${Offline} health=${health}>You can open every designer and set your choices. No sheet can be made until it is back.<//>
    <${DesignReel} list=${list} open=${open}/>
    <p class="lk-plain">Designers turn a few choices into a finished concept and a whole sheet of views: products, vehicles, settings, animals, plants, hair, nails, furniture and costumes. The options come from the studio's own designer modules. Everything is original: no brands, logos or real makes and models.</p></div>`;
  return html`<div class="lk de-page"><button class="btn small de-back" onClick=${() => { location.hash = "design"; }}>All designers</button><${Head}>${pack.label}<//><${Offline} health=${health}>You can set your choices here. No sheet can be made until it is back.<//>
    <div class="de-prompt film" aria-live="polite"><span class="lk-kick">${views[0] ? `The words for "${views[0]}"` : "The words"}, from this designer's own composer</span><p>${promptText || "Reading the composer..."}</p><small>Change a choice below and this changes with it. This exact text goes to the model. No picture is made until you press Make.</small></div>
    <div class="de-layout"><div class="card"><h3>Your design</h3>
      <textarea placeholder="Your idea in a few words (optional)" value=${idea} onInput=${(e) => setIdea(e.target.value)} aria-label="idea"></textarea>
      ${["tshirt", "mug", "printify"].includes(pack.id) && html`<input type="text" style="margin-top:8px" placeholder="Exact words on the product (optional)" value=${words} onInput=${(e) => setWords(e.target.value)} aria-label="words"/>`}
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:10px;margin-top:12px">${pack.groups.map((g) => html`<label class="small" style="display:block">${g.label}<select value=${choices[g.id] || ""} onChange=${(e) => setChoices({ ...choices, [g.id]: e.target.value })} style="width:100%;margin-top:3px;background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:10px;padding:8px"><option value="">any</option>${g.categories ? Object.entries(g.categories).map(([c, o]) => html`<optgroup label=${c}>${o.map((x) => html`<option value=${x}>${x}</option>`)}</optgroup>`) : g.options.map((x) => html`<option value=${x}>${x}</option>`)}</select></label>`)}</div>
      <h3 style="margin-top:14px">Views in the sheet</h3><div class="row" style="margin:0">${pack.views.map((v) => html`<button class=${"chip" + (views.includes(v) ? " on" : "")} onClick=${() => toggle(v)}>${v.length > 34 ? v.slice(0, 32) + "..." : v}</button>`)}</div>
      <div class="row"><label class="small">Model <select value=${goal} onChange=${(e) => setGoal(e.target.value)} style="background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:10px;padding:8px">${engines.map((g) => html`<option value=${g.id}>${g.label}: ${g.family} (${g.license_class === "open" ? "Apache-2.0" : "community licence"})</option>`)}</select></label><span class="grow"></span><button class="btn primary" disabled=${busy} onClick=${make}>${busy ? "Making the sheet..." : `Make ${views.length || 1} view${views.length === 1 ? "" : "s"}`}</button></div>
      ${err && html`<p class="small" style="color:var(--err)">${err}</p>`}</div>
      <div class="card"><h3>Sheet</h3>${!results.length && html`<figure class="de-sample film"><img key=${sample.src} src=${sample.src} alt="" onError=${(e) => { e.target.closest("figure").style.display = "none"; }}/><figcaption>${sample.note}</figcaption></figure><p class="small" style="margin:0">Your views appear here, one by one.</p>`}
        <div class="thumbs" style="grid-template-columns:repeat(auto-fill,minmax(150px,1fr))">${results.map((r) => html`<div><div class="thumb" style="aspect-ratio:1">${r.files ? html`<img src=${r.files[0].url} alt=${r.view} loading="lazy"/>` : html`<div style="display:grid;place-items:center;height:100%" class="small">${r.error ? "failed" : "rendering..."}</div>`}</div><div class="small" style="margin-top:4px">${r.view.slice(0, 40)}</div></div>`)}</div></div></div>${pack.id === "fashion" && html`<${TryOn}/>`}</div>`;
}

/* ---------- Apps: any ComfyUI app (workflow + exposed inputs) runs here as a simple form ---------- */
const APP_PEEK = 10;      // in the "Everything" view each shelf shows its first ten; its own chapter, a search or "Show all" shows the rest
export function Apps() {
  const [apps, setApps] = useState(null); const [app, setApp] = useState(null); const [vals, setVals] = useState({}); const [permission, setPermission] = useState(false); const [res, setRes] = useState(null); const [busy, setBusy] = useState(false); const [err, setErr] = useState(""); const [ok, setOk] = useState(false); const [packs, setPacks] = useState(null); const [msg, setMsg] = useState("");
  const health = useHealth(); const every = useAllGraphs(), rows = every.rows, cnt = every.counts; const [shots, setShots] = useState([]); const [q, setQ] = useState(""); const [sec, setSec] = useState("all"); const [whole, setWhole] = useState({});
  useEffect(() => { api("/api/apps").then((d) => setApps(d.apps)).catch((e) => { setApps([]); }); fetch("showcase/showcase.json").then((r) => r.json()).then(setShots).catch(() => {}); }, []);
  const hit = (...t) => { const w = q.trim().toLowerCase(); return !w || t.join(" ").toLowerCase().includes(w); };
  const [graphRow, setGraphRow] = useState(null);
  const tile = (art, tag, title, sub, on, key) => html`<button key=${key} class="appg" onClick=${on}><span class=${"appgart" + (art ? "" : " ap-noart")}><em class="ap-glyph" aria-hidden="true">${String(title).split(/[\s:(]/)[0]}</em>${art && html`<img src=${art} alt="" loading="lazy" onError=${(e) => e.target.remove()}/>`}<i>${tag}</i></span><b>${title}</b><small>${sub}</small></button>`;
  const open = async (id) => {
    setErr(""); setRes(null); setMsg(""); setPacks(null);
    try { const d = await api("/api/apps/" + id); setApp(d); const v = {}; d.inputs.forEach((i) => { if (i.default !== undefined && i.default !== null && i.type !== "image") v[i.key] = i.default; }); setVals(v); if (d.unknown_nodes.length) setPacks((await api(`/api/apps/${id}/packs`)).packs); } catch (e) { setErr(e.message); }
  };
  const upload = async (key, f) => { if (!f) return; const fd = new FormData(); fd.append("file", f); try { const r = await api("/api/upload", { method: "POST", body: fd }); setVals({ ...vals, [key]: r.name }); } catch (e) { setErr(e.message); } };
  const run = async () => {
    setBusy(true); setErr(""); setRes(null);
    try { const { job } = await post(`/api/apps/${app.id}/run`, app.likeness ? { values: vals, permission } : { values: vals }); for (let i = 0; i < 800; i++) { await sleep(1500); const s = await api("/api/jobs/" + job); if (s.status === "done") { setRes(s); break; } if (s.status === "error") { setErr(s.error || "the app failed"); break; } } } catch (e) { setErr(e.message); }
    setBusy(false);
  };
  const fetchModels = async () => { setMsg("Downloading, this can take a while..."); try { const r = await post(`/api/apps/${app.id}/fetch-models`, { confirm: ok }); setMsg("Saved " + r.saved.length + " file(s). Reloading..."); await open(app.id); } catch (e) { setMsg(e.message); } };
  if (!app) { const of = (k) => rows.filter((r) => sectionOf(r) === k && matches(r, q)), G = of("goal"), M3 = of("model3d"), TO = of("tryon"), MO = of("motion"), W = of("workflow"), F = of("family"), R = of("recipe"), H = (apps || []).filter((a) => hit(a.title)), all = rows.length + (apps || []).length, on = (x) => sec === "all" || sec === x;
    const chip = (k, l) => html`<button class=${"chip" + (sec === k ? " on" : "")} onClick=${() => setSec(k)}>${l}</button>`;
    const lead = rows.filter((g) => g.kind === "goal").map((g) => { const m = shots.find((x) => x.goal === g.id && x.poster); return m ? { id: g.id, src: m.src, poster: m.poster, kind: m.kind, title: g.label, sub: g.sub, kicker: "Our render" } : null; }).filter(Boolean);
    const leadPicks = lead.filter((x, i) => lead.findIndex((y) => y.poster === x.poster) === i).filter((x) => x.kind === "image" || !/chef/.test(x.src)).slice(0, 6);
    return html`<div class="lk ap-page">
    <div class="lk-lead"><p class="lk-plain">Everything this studio runs, packaged as something you can open and run on your own GPU. If a graph needs a model you don't have, its page says what to download. A runner or a tool is a small program rather than a graph, and its tile says so.</p><${Stats} items=${[[all, "ways to run"], [cnt.goal || 0, "studio apps"], [new Set(rows.filter((g) => g.kind === "family" && g.slug).map((g) => g.slug)).size, "families"]]}/></div>
    <${Offline} health=${health}>You can browse every graph and read its code. Nothing can run until it is back.<//>
    ${leadPicks.length > 0 && html`<${Stage} items=${leadPicks} label="Studio apps" note="These are our own renders, not yours."/>`}
    ${err && html`<p class="small" style="color:var(--err)" role="alert">${err}</p>`}
    <${Strip} label="Which graphs" value=${sec} onPick=${setSec} items=${[{ k: "all", b: "Everything", s: `${all} in all` }, { k: "goal", b: "Studio apps", s: `${cnt.goal || 0} built in` }, { k: "model3d", b: "3D models", s: `${cnt.model3d || 0} ways` }, { k: "tryon", b: "Try-on", s: `${cnt.tryon || 0} runners` }, { k: "motion", b: "Motion", s: `${cnt.motion || 0} routes` }, { k: "workflow", b: "World Kit and Virtual Set", s: `${cnt.workflow || 0} graphs` }, { k: "family", b: "Family graphs", s: `${cnt.family || 0} templates` }, { k: "recipe", b: "Recipes", s: `${cnt.recipe || 0} chained` }, ...((apps || []).length > 0 ? [{ k: "hub", b: "Hub apps", s: `${apps.length} added` }] : [])]}/>
    <input class="ap-search" type="search" placeholder="Search every graph by name, family or what it does" aria-label="Search graphs" value=${q} onInput=${(e) => setQ(e.target.value)}/>
    ${[["goal", "Studio apps", G], ["model3d", "3D models", M3], ["tryon", "Try-on", TO], ["motion", "Motion", MO], ["workflow", "World Kit and Virtual Set", W], ["family", "Family graphs", F], ["recipe", "Recipes", R]].map(([k, title, list]) => on(k) && list.length > 0 && html`<section key=${k}><div class="psec"><h3>${title}</h3><span>${list.length}</span></div><div class="appgrid">${(sec === "all" && !q.trim() && !whole[k] ? list.slice(0, APP_PEEK) : list).map((r) => tile(r.art || ((shots.find((x) => x.goal === r.id && x.poster)) || {}).poster, tagOf(r), r.label, r.kind === "runner" || r.kind === "tool" ? `Not a ComfyUI graph. ${r.sub}` : r.cat || r.sub, () => setGraphRow(r), r.key))}</div>${sec === "all" && !q.trim() && !whole[k] && list.length > APP_PEEK && html`<button type="button" class="ap-more" onClick=${() => setWhole({ ...whole, [k]: true })}>Show all ${list.length} in ${title}</button>`}</section>`)}
    ${on("hub") && H.length > 0 && html`<section><div class="psec"><h3>Hub apps</h3><span>${H.length}</span></div><div class="appgrid">${H.map((a) => tile(null, a.runnable ? "Ready" : a.missing_models.length ? `Needs ${a.missing_models.length} file${a.missing_models.length > 1 ? "s" : ""}` : "Needs nodes", a.title, `${a.inputs} input${a.inputs === 1 ? "" : "s"}, ${a.outputs} output${a.outputs === 1 ? "" : "s"}`, () => open(a.id), a.id))}</div></section>`}
    ${!all && !err && html`<p class="small">Loading every graph...</p>`}${all > 0 && !G.length && !M3.length && !TO.length && !W.length && !R.length && !F.length && !H.length && html`<p class="small">Nothing matches. Try fewer words.</p>`}
    ${graphRow && html`<${GraphPanel} row=${graphRow} onClose=${() => setGraphRow(null)}/>`}</div>`; }
  return html`<div class="lk ap-page"><button class="btn small ap-back" onClick=${() => setApp(null)}>All apps</button><${Head}>${app.title}<//>
    <div class="ap-layout"><div class="card"><h3>Inputs</h3>
      ${app.likeness && html`<label class="small" style="display:flex;gap:8px;margin:10px 0"><input type="checkbox" checked=${permission} onChange=${(e) => setPermission(e.target.checked)}/><span>The person shown is invented, or has given permission for their face, voice and body to be used this way.</span></label>`}
      ${app.inputs.map((i) => html`<label class="small" style="display:block;margin:10px 0">${i.label}
        ${i.type === "image" ? html`<div class="row" style="margin:4px 0"><input type="file" accept="image/png,image/jpeg,image/webp" onChange=${(e) => upload(i.key, e.target.files[0])}/>${vals[i.key] && html`<span class="small">${vals[i.key]}</span>`}</div>` :
          i.type === "choice" ? html`<select value=${vals[i.key] ?? ""} onChange=${(e) => setVals({ ...vals, [i.key]: e.target.value })} style="width:100%;margin-top:3px;background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:10px;padding:8px">${(i.options || []).map((o) => html`<option value=${o}>${o}</option>`)}</select>` :
          i.type === "number" ? html`<input type="text" inputmode="decimal" value=${vals[i.key] ?? ""} onInput=${(e) => setVals({ ...vals, [i.key]: e.target.value === "" || isNaN(+e.target.value) ? e.target.value : +e.target.value })} style="margin-top:3px"/>` :
          i.type === "bool" ? html`<div><input type="checkbox" checked=${!!vals[i.key]} onChange=${(e) => setVals({ ...vals, [i.key]: e.target.checked })}/></div>` :
          html`<textarea value=${vals[i.key] ?? ""} onInput=${(e) => setVals({ ...vals, [i.key]: e.target.value })} style="min-height:70px;margin-top:3px"></textarea>`}</label>`)}
      ${app.downloads.length > 0 && html`<div class="card" style="margin:12px 0;border-color:var(--warn)"><h3>Missing model files</h3><ul class="small" style="margin:0 0 8px;padding-left:18px">${app.downloads.map((d) => html`<li>${d.name} <span style="opacity:.7">(${d.directory})</span></li>`)}</ul>
        <label class="small"><input type="checkbox" checked=${ok} onChange=${(e) => setOk(e.target.checked)}/> Download these from Hugging Face to this machine</label><div class="row"><button class="btn small" disabled=${!ok} onClick=${fetchModels}>Download missing files</button></div>${msg && html`<p class="small">${msg}</p>`}</div>`}
      ${packs && Object.keys(packs).length > 0 && html`<div class="card" style="margin:12px 0;border-color:var(--warn)"><h3>Needs custom nodes</h3><ul class="small" style="margin:0;padding-left:18px">${Object.entries(packs).map(([n, r]) => html`<li>${n}: ${r ? html`<a href=${r} target="_blank" rel="noopener noreferrer">${r.replace("https://github.com/", "")}</a>` : "pack not found in the registry"}</li>`)}</ul><p class="small" style="margin:6px 0 0">Clone the pack into ComfyUI's custom_nodes folder, install its requirements, and restart ComfyUI.</p></div>`}
      <div class="row"><span class="grow"></span><button class="btn primary" disabled=${busy || !app.ready || app.downloads.length > 0} onClick=${run}>${busy ? "Running..." : "Run app"}</button></div>
      ${err && html`<p class="small" style="color:var(--err)">${err}</p>`}</div>
      <div class="card"><h3>Result</h3>${!res && html`<p class="small" style="margin:0">${busy ? "Running on your GPU..." : "Outputs appear here."}</p>`}
        ${res && res.files.map((f) => f.kind === "video" ? html`<video src=${f.url} controls style="max-width:100%;border-radius:12px;margin-bottom:8px"></video>` : f.kind === "audio" ? html`<audio src=${f.url} controls style="width:100%"></audio>` : html`<img src=${f.url} alt="" style="max-width:100%;border-radius:12px;margin-bottom:8px"/>`)}</div></div></div>`;
}
