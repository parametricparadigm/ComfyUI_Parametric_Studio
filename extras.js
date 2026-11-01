import { useState, useEffect } from "preact/hooks";
import { html, api, post } from "./common.js";
import { Viewer3D } from "./viewer3d.js";
import { Face, familyLabel } from "./prime_ui.js";
import { GraphPanel } from "./apipage.js";
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
  const tiers = ["family", "secondary", "tertiary"]; const label = { family: "Model specialists", secondary: "Shared experts", tertiary: "Fine-tuning experts" };
  const prime = (members || []).find((m) => m.tier === "master"); const say = state.speaking === "master"; const [tier, setTier] = useState("all"); const inTier = (t) => (members || []).filter((m) => m.tier === t).length;
  return html`<div class="lk cr-page">${err && html`<p class="small" style="color:var(--err)" role="alert">${err}</p>`}
    <div class="crewtop">${prime && html`<button class=${"crewprime" + (say ? " speaking" : "")} onClick=${() => dispatchEvent(new CustomEvent("crew-talk", { detail: prime }))} aria-label="Talk to Comfy Prime"><${Face} member=${prime} speaking=${say}/><span class="ctext"><b>${prime.name}</b><small>Your guide. Holds every specialist's notes and learns your name.</small><em>Talk to me</em></span></button>`}
      <div class="crewask"><p>Every model family has a specialist who has read all our notes on it. Click a face to talk to them: they answer aloud, only from those notes, and show the exact quote so you can check them.</p>
        <div class="row" style="margin:0"><input type="text" placeholder="Or ask whoever knows best, e.g. how many steps should Klein use?" value=${q} onInput=${(e) => setQ(e.target.value)} onKeyDown=${(e) => e.key === "Enter" && ask()} aria-label="question for the crew"/><button class="btn primary" onClick=${ask} disabled=${q.trim().length < 3}>Ask</button></div></div></div>
    ${members && html`<${Strip} label="Which specialists" value=${tier} onPick=${setTier} items=${[{ k: "all", b: "Everyone", s: `${members.filter((m) => m.tier !== "master").length} specialists` }, ...tiers.filter((t) => inTier(t)).map((t) => ({ k: t, b: label[t], s: `${inTier(t)} on the crew` }))]}/>`}
    ${members && tiers.filter((t) => tier === "all" || tier === t).map((t) => { const l = members.filter((m) => m.tier === t); return l.length ? html`<div class="sect crewsect"><h2>${label[t]}</h2></div><div class="crewgrid">${l.map((m) => html`<${CrewCard} key=${m.id} m=${m} state=${state}/>`)}</div>` : null; })}
    ${!members && !err && html`<p class="small">Loading the crew...</p>`}</div>`;
}

/* ---------- Site builder ---------- */
const SITE_EXAMPLES = [
  { label: "Bakery", name: "Golden Crumb", brand: "warm, handmade, gold and cream", pages: "home, menu, about, contact", facts: [["Hours", "Tuesday to Sunday, 7 to 3"], ["Known for", "Sourdough baked before dawn"], ["Where", "Corner of Pine and 4th"]] },
  { label: "Band", name: "The Night Shift", brand: "dark, loud, neon green", pages: "home, shows, music, contact", facts: [["Sound", "Three-piece synth rock"], ["Next show", "Friday at the Old Mill"], ["Booking", "Use the contact form"]] },
  { label: "Studio", name: "Parallel Frame", brand: "minimal, cinematic, black and white", pages: "home, work, services, contact", facts: [["What we do", "Short films and product videos"], ["Team", "Two directors and an editor"], ["Turnaround", "Two weeks"]] },
];
const SITE_ART = ["showcase/p_teapot.webp", "showcase/a_score.webp", "showcase/short_film.webp"];
export function Site() {
  const [name, setName] = useState(""); const [brand, setBrand] = useState(""); const [pages, setPages] = useState("home, about, contact"); const [facts, setFacts] = useState([["", ""], ["", ""], ["", ""]]); const [busy, setBusy] = useState(false); const [err, setErr] = useState(""); const [site, setSite] = useState(null);
  const go = async () => {
    setBusy(true); setErr(""); setSite(null);
    const f = Object.fromEntries(facts.filter(([k, v]) => k.trim() && v.trim()));
    try { const r = await post("/api/site/build", { brief: { name, brand, pages: pages.split(",").map((x) => x.trim()).filter(Boolean), facts: f } }); if ((r.files || []).length) setSite(r); else setErr((r.problems || []).join("; ") || "The site could not be built."); } catch (e) { setErr(e.message); }
    setBusy(false);
  };
  const fill = (x) => { setName(x.name); setBrand(x.brand); setPages(x.pages); setFacts(x.facts); };
  const facing = busy ? "Building your site." : "Your site shows up here.";
  return html`<div class="lk st-page">
    <p class="lk-plain">Describe a small business or project and the studio writes and builds a clean, accessible, safe-for-work website from your facts only. It never invents details. A local AI writes the pages, the studio builds them, and you keep clean files to host anywhere. Open it, or hand it to your editor.</p>
    <section aria-labelledby="st-ex"><${Head} n=${1} id="st-ex" sub="Each one fills in the form below, and nothing runs until you press Build. The pictures are our own renders, not websites.">Start from an example<//>
      <div class="st-examples">${SITE_EXAMPLES.map((x, i) => html`<button key=${x.label} type="button" class="st-example" onClick=${() => fill(x)}><img src=${SITE_ART[i]} alt="" loading="lazy"/><span class="st-exshade"></span><span class="st-extext"><b>${x.label}</b><small>${x.name}: ${x.brand}</small></span></button>`)}</div></section>
    <div class="st-work">
      <section class="card st-brief" aria-labelledby="st-b"><${Head} n=${2} id="st-b">Your brief<//>
        <label class="lk-field">Name (required)<input type="text" value=${name} onInput=${(e) => setName(e.target.value)}/></label>
        <label class="lk-field">Brand voice<input type="text" placeholder="e.g. warm, playful, precise" value=${brand} onInput=${(e) => setBrand(e.target.value)}/></label>
        <label class="lk-field">Pages (comma separated)<input type="text" value=${pages} onInput=${(e) => setPages(e.target.value)}/></label>
        <h3>Facts the copy may use</h3>
        ${facts.map((p, i) => html`<div class="st-fact"><input type="text" placeholder="e.g. hours" value=${p[0]} onInput=${(e) => setFacts(facts.map((x, j) => (j === i ? [e.target.value, x[1]] : x)))} aria-label=${`Fact ${i + 1} name`}/><input type="text" placeholder="e.g. Mon-Fri 9 to 5" value=${p[1]} onInput=${(e) => setFacts(facts.map((x, j) => (j === i ? [x[0], e.target.value] : x)))} aria-label=${`Fact ${i + 1} text`}/></div>`)}
        <button class="btn primary st-go" disabled=${busy || !name.trim()} onClick=${go}>${busy ? "Building..." : "Build the site"}</button>${err && html`<p class="small" style="color:var(--err)" role="alert">${err}</p>`}</section>
      <section class="card st-preview" aria-labelledby="st-p"><${Head} n=${3} id="st-p">Preview<//>${site ? html`<iframe title="site preview" sandbox="" src=${`/api/site/${site.site_id}/index.html`} class="st-frame"></iframe><div class="row"><a class="btn small" target="_blank" rel="noopener noreferrer" href=${`/api/site/${site.site_id}/index.html`}>Open in a tab</a><span class="small">${(site.files || []).length} files</span></div>${(site.problems || []).length > 0 && html`<p class="small warn" style="margin:8px 0 0">${site.problems.join("; ")}</p>`}` : html`<div class="st-blank" role="status"><b>${facing}</b><p>Nothing has been made yet. The preview opens here when the build finishes.</p></div>`}</section>
    </div></div>`;
}

/* ---------- 3D ---------- */
const MAKE_3D = [["#worldkit", "wk_art/street_above.webp", "World Kit", "Real-scale places, props and looks, built on this machine."], ["#processes", "wk_art/knot.webp", "Processes", "Each photo-to-3D method says here whether it opens today."], ["#virtualset", "wk_art/cafe.webp", "Virtual Set", "Direct a video from a 3D scene."]];
export function Studio3D() {
  const [items, setItems] = useState([]); const [sel, setSel] = useState("/api/sample.glb"); const [err, setErr] = useState("");
  useEffect(() => { api("/api/models3d").then((d) => setItems(d.items)).catch((e) => setErr(e.message)); }, []);
  const name = sel === "/api/sample.glb" ? "Sample knot" : ((items.find((m) => m.url === sel) || {}).path || "").split("/").pop();
  return html`<div class="lk v3-page"><p class="lk-plain">Look at 3D results straight from the studio: drag to orbit, scroll to zoom. The gold knot is a built-in sample; models generated by the 3D pipelines appear below as soon as they exist.</p>
    ${err && html`<p class="small" style="color:var(--err)" role="alert">${err}</p>`}
    <section aria-labelledby="v3-look"><${Head} n=${1} id="v3-look">Orbit it<//>
      <div class="v3-stage film"><div class="v3-view"><${Viewer3D} key=${sel} url=${sel} height="100%" background=${0x0b0d0b} label=${"3D view of " + name}/></div>
        <div class="v3-side"><${Stats} items=${[[items.length, items.length === 1 ? "generated model" : "generated models"]]}/><h3>Models</h3><ul class="v3-list"><li><button class=${"chip" + (sel === "/api/sample.glb" ? " on" : "")} aria-pressed=${sel === "/api/sample.glb"} onClick=${() => setSel("/api/sample.glb")}>Sample knot</button></li>${items.map((m) => html`<li key=${m.url}><button class=${"chip" + (sel === m.url ? " on" : "")} aria-pressed=${sel === m.url} onClick=${() => setSel(m.url)}>${m.path.split("/").pop()}</button></li>`)}</ul>${!items.length && html`<p class="small">No generated .glb files yet. Until there is one, you are looking at the sample, not your work.</p>`}</div></div></section>
    <section aria-labelledby="v3-make"><${Head} n=${2} id="v3-make" sub="The pictures are our own test builds, not yours.">Make one to look at<//>
      <div class="lk-tiles">${MAKE_3D.map(([href, art, t, sub]) => html`<a key=${href} class="lk-tile v3-make" href=${href}><span class="lk-tilepic"><img src=${art} alt="" loading="lazy"/></span><span class="lk-tilebody"><b>${t}</b><small>${sub}</small></span></a>`)}</div></section></div>`;
}

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

/* ---------- Designers: pick options from the owner's designer modules, render a sheet of views ---------- */
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function runJob(body) {
  const { job } = await post("/api/generate", body);
  for (let i = 0; i < 600; i++) { await sleep(1500); const s = await api("/api/jobs/" + job); if (s.status === "done") return s; if (s.status === "error") throw new Error(s.error || "the job failed"); }
  throw new Error("timed out");
}
/* one plain line per designer for its tile; the picture is a real render from the designer's own composer (scripts/build_designer_art.py) */
const DESIGNER_LINE = { character: "Original adult characters, headshots to full body", fashion: "Outfits, shoes and accessories as a sheet", tshirt: "Tees and sweats, print by print", mug: "Mugs with your own artwork", printify: "Art on print-on-demand products", vehicle: "Cars, bikes and wild builds", setting: "Rooms, places and moods", animal: "Any animal, in any light", plant: "Houseplants to whole gardens", hair: "Cuts, colours and textures", nail: "Nail shapes, finishes and art", furniture: "Furniture in any style", cosplay: "Original costumes, armour to props" };
function PrintifyCard() {
  const [p, setP] = useState(null); const [tok, setTok] = useState(""); const [err, setErr] = useState("");
  useEffect(() => { api("/api/printify").then(setP).catch(() => {}); }, []);
  if (!p) return null;
  const go = async () => { setErr(""); try { setP(await post("/api/printify/connect", { token: tok })); setTok(""); } catch (e) { setErr(e.message); } };
  return html`<div class="card" style="margin:0 0 14px"><h3>Connect your Printify</h3>${p.connected ? html`<p class="small">Connected: ${p.shops.map((s) => s.title).join(", ") || "no shops yet"}. Finished products can go to your shop as drafts; nothing is published.</p>` : html`<p class="small">Paste a Printify personal access token to send designs to your own shop as drafts. It stays on this computer.</p><div class="row"><input type="text" placeholder="Printify token" value=${tok} onInput=${(e) => setTok(e.target.value)} aria-label="Printify token" style="max-width:420px"/><button class="btn small primary" disabled=${!tok.trim()} onClick=${go}>Connect</button></div>`}${err && html`<p class="small" style="color:var(--err)">${err}</p>`}</div>`;
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
  if (!pack || !packId) return html`<div class="lk de-page">${health && health.edition === "extended" && html`<${PrintifyCard}/>`}<p class="lk-plain">Designers turn a few choices into a finished concept and a whole sheet of views: products, vehicles, settings, animals, plants, hair, nails, furniture and costumes. The options come from the studio's own designer modules. Everything is original: no brands, logos or real makes and models.</p>
    ${err && html`<p class="small" style="color:var(--err)" role="alert">${err}</p>`}<${Offline} health=${health}>You can open every designer and set your choices. No sheet can be made until it is back.<//><div class="dgrid">${list.map((p) => html`<button class="gcard" onClick=${() => open(p.id)} aria-label=${p.label}><div class="gmedia gblank">${p.label[0]}</div><img class="gmedia" src=${"designer_art/" + p.id + ".webp"} alt="" loading="lazy" onError=${(e) => { e.target.style.display = "none"; }}/><span class="gshade"></span><span class="gflag">${p.views} views</span><span class="glic">${p.groups} choices</span><span class="gtext"><b>${p.label}</b><small>${DESIGNER_LINE[p.id] || "A full sheet of views"}</small></span></button>`)}</div></div>`;
  return html`<div class="lk de-page"><button class="btn small de-back" onClick=${() => { location.hash = "design"; }}>All designers</button><${Head}>${pack.label}<//><${Offline} health=${health}>You can set your choices here. No sheet can be made until it is back.<//>
    <div class="de-layout"><div class="card"><h3>Your design</h3>
      <textarea placeholder="Your idea in a few words (optional)" value=${idea} onInput=${(e) => setIdea(e.target.value)} aria-label="idea"></textarea>
      ${["tshirt", "mug", "printify"].includes(pack.id) && html`<input type="text" style="margin-top:8px" placeholder="Exact words on the product (optional)" value=${words} onInput=${(e) => setWords(e.target.value)} aria-label="words"/>`}
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:10px;margin-top:12px">${pack.groups.map((g) => html`<label class="small" style="display:block">${g.label}<select value=${choices[g.id] || ""} onChange=${(e) => setChoices({ ...choices, [g.id]: e.target.value })} style="width:100%;margin-top:3px;background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:10px;padding:8px"><option value="">any</option>${g.categories ? Object.entries(g.categories).map(([c, o]) => html`<optgroup label=${c}>${o.map((x) => html`<option value=${x}>${x}</option>`)}</optgroup>`) : g.options.map((x) => html`<option value=${x}>${x}</option>`)}</select></label>`)}</div>
      <h3 style="margin-top:14px">Views in the sheet</h3><div class="row" style="margin:0">${pack.views.map((v) => html`<button class=${"chip" + (views.includes(v) ? " on" : "")} onClick=${() => toggle(v)}>${v.length > 34 ? v.slice(0, 32) + "..." : v}</button>`)}</div>
      <div class="row"><label class="small">Model <select value=${goal} onChange=${(e) => setGoal(e.target.value)} style="background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:10px;padding:8px">${engines.map((g) => html`<option value=${g.id}>${g.label}: ${g.family} (${g.license_class === "open" ? "Apache-2.0" : "community licence"})</option>`)}</select></label><span class="grow"></span><button class="btn primary" disabled=${busy} onClick=${make}>${busy ? "Making the sheet..." : `Make ${views.length || 1} view${views.length === 1 ? "" : "s"}`}</button></div>
      ${err && html`<p class="small" style="color:var(--err)">${err}</p>`}</div>
      <div class="card"><h3>Sheet</h3>${!results.length && html`<figure class="de-sample film"><img src=${"designer_art/" + pack.id + ".webp"} alt="" loading="lazy" onError=${(e) => { e.target.closest("figure").style.display = "none"; }}/><figcaption>Our own render from this designer, not yours.</figcaption></figure><p class="small" style="margin:0">Your views appear here, one by one.</p>`}
        <div class="thumbs" style="grid-template-columns:repeat(auto-fill,minmax(150px,1fr))">${results.map((r) => html`<div><div class="thumb" style="aspect-ratio:1">${r.files ? html`<img src=${r.files[0].url} alt=${r.view} loading="lazy"/>` : html`<div style="display:grid;place-items:center;height:100%" class="small">${r.error ? "failed" : "rendering..."}</div>`}</div><div class="small" style="margin-top:4px">${r.view.slice(0, 40)}</div></div>`)}</div></div></div></div>`;
}

/* ---------- Apps: any ComfyUI app (workflow + exposed inputs) runs here as a simple form ---------- */
export function Apps() {
  const [apps, setApps] = useState(null); const [app, setApp] = useState(null); const [vals, setVals] = useState({}); const [res, setRes] = useState(null); const [busy, setBusy] = useState(false); const [err, setErr] = useState(""); const [ok, setOk] = useState(false); const [packs, setPacks] = useState(null); const [msg, setMsg] = useState("");
  const health = useHealth(); const [graphs, setGraphs] = useState([]); const [recipes, setRecipes] = useState([]); const [famg, setFamg] = useState([]); const [shots, setShots] = useState([]); const [q, setQ] = useState(""); const [sec, setSec] = useState("all");
  useEffect(() => { api("/api/apps").then((d) => setApps(d.apps)).catch((e) => { setApps([]); }); api("/api/graphs").then(setGraphs).catch(() => {}); api("/api/recipes").then((d) => setRecipes(d.recipes || d)).catch(() => {}); api("/api/family-graphs").then((d) => setFamg(d.graphs)).catch(() => {}); fetch("showcase/showcase.json").then((r) => r.json()).then(setShots).catch(() => {}); }, []);
  const hit = (...t) => { const w = q.trim().toLowerCase(); return !w || t.join(" ").toLowerCase().includes(w); };
  const [graphRow, setGraphRow] = useState(null);
  const tile = (art, tag, title, sub, on, key) => html`<button key=${key} class="appg" onClick=${on}><span class="appgart">${art && html`<img src=${art} alt="" loading="lazy" onError=${(e) => e.target.remove()}/>`}<i>${tag}</i></span><b>${title}</b><small>${sub}</small></button>`;
  const open = async (id) => {
    setErr(""); setRes(null); setMsg(""); setPacks(null);
    try { const d = await api("/api/apps/" + id); setApp(d); const v = {}; d.inputs.forEach((i) => { if (i.default !== undefined && i.default !== null && i.type !== "image") v[i.key] = i.default; }); setVals(v); if (d.unknown_nodes.length) setPacks((await api(`/api/apps/${id}/packs`)).packs); } catch (e) { setErr(e.message); }
  };
  const upload = async (key, f) => { if (!f) return; const fd = new FormData(); fd.append("file", f); try { const r = await api("/api/upload", { method: "POST", body: fd }); setVals({ ...vals, [key]: r.name }); } catch (e) { setErr(e.message); } };
  const run = async () => {
    setBusy(true); setErr(""); setRes(null);
    try { const { job } = await post(`/api/apps/${app.id}/run`, { values: vals }); for (let i = 0; i < 800; i++) { await sleep(1500); const s = await api("/api/jobs/" + job); if (s.status === "done") { setRes(s); break; } if (s.status === "error") { setErr(s.error || "the app failed"); break; } } } catch (e) { setErr(e.message); }
    setBusy(false);
  };
  const fetchModels = async () => { setMsg("Downloading, this can take a while..."); try { const r = await post(`/api/apps/${app.id}/fetch-models`, { confirm: ok }); setMsg("Saved " + r.saved.length + " file(s). Reloading..."); await open(app.id); } catch (e) { setMsg(e.message); } };
  if (!app) { const G = graphs.filter((g) => hit(g.label, g.model)), R = recipes.filter((r) => hit(r.title || r.name || r.id, r.what || r.description || "")), F = famg.filter((g) => hit(g.title, g.family, g.cat, g.desc)), H = (apps || []).filter((a) => hit(a.title)), all = graphs.length + recipes.length + famg.length + (apps || []).length, on = (x) => sec === "all" || sec === x;
    const chip = (k, l) => html`<button class=${"chip" + (sec === k ? " on" : "")} onClick=${() => setSec(k)}>${l}</button>`;
    const lead = graphs.map((g) => { const m = shots.find((x) => x.goal === g.goal && x.poster); return m ? { id: g.goal, src: m.src, poster: m.poster, kind: m.kind, title: g.label, sub: g.model, kicker: "Our render" } : null; }).filter(Boolean);
    const leadPicks = lead.filter((x, i) => lead.findIndex((y) => y.poster === x.poster) === i).filter((x) => x.kind === "image" || !/chef/.test(x.src)).slice(0, 6);
    return html`<div class="lk ap-page">
    <div class="lk-lead"><p class="lk-plain">Every workflow in this studio, packaged as something you can open and run on your own GPU. If a graph needs a model you don't have, its page says what to download.</p><${Stats} items=${[[all, "graphs"], [graphs.length, "studio apps"], [new Set(famg.map((g) => g.slug)).size, "families"]]}/></div>
    <${Offline} health=${health}>You can browse every graph and read its code. Nothing can run until it is back.<//>
    ${leadPicks.length > 0 && html`<${Stage} items=${leadPicks} label="Studio apps" note="These are our own renders, not yours."/>`}
    ${err && html`<p class="small" style="color:var(--err)" role="alert">${err}</p>`}
    <${Strip} label="Which graphs" value=${sec} onPick=${setSec} items=${[{ k: "all", b: "Everything", s: `${all} graphs` }, { k: "studio", b: "Studio apps", s: `${graphs.length} built in` }, { k: "recipes", b: "Recipes", s: `${recipes.length} chained` }, { k: "family", b: "Family graphs", s: `${famg.length} templates` }, ...((apps || []).length > 0 ? [{ k: "hub", b: "Hub apps", s: `${apps.length} added` }] : [])]}/>
    <input class="ap-search" type="search" placeholder="Search every graph by name, family or what it does" aria-label="Search graphs" value=${q} onInput=${(e) => setQ(e.target.value)}/>
    ${on("studio") && G.length > 0 && html`<section><div class="psec"><h3>Studio apps</h3><span>${G.length}</span></div><div class="appgrid">${G.map((g) => tile(((shots.find((x) => x.goal === g.goal && x.poster)) || {}).poster, "App", g.label, g.model, () => setGraphRow({ key: "goal:" + g.goal, kind: "goal", id: g.goal, label: g.label, sub: g.model }), g.goal))}</div></section>`}
    ${on("recipes") && R.length > 0 && html`<section><div class="psec"><h3>Recipes</h3><span>${R.length}</span></div><div class="appgrid">${R.map((r) => tile(((shots.find((x) => x.goal === ((r.steps || []).map((st) => st.goal).find(Boolean)) && x.poster)) || {}).poster, "Recipe", r.title || r.name || r.id, r.what || r.description || "", () => setGraphRow({ key: "recipe:" + r.id, kind: "recipe", id: r.id, label: r.title || r.name || r.id, sub: (r.models || []).map((m) => m.name || m).join(", ") || "Recipe" }), r.id))}</div></section>`}
    ${on("family") && F.length > 0 && html`<section><div class="psec"><h3>Family graphs</h3><span>${F.length}</span></div><div class="appgrid">${F.map((g) => tile(g.art, g.family, g.title, g.cat, () => setGraphRow({ key: `family:${g.slug}/${g.name}`, kind: "family", id: g.name, slug: g.slug, label: g.title, sub: g.family }), g.slug + g.name))}</div></section>`}
    ${on("hub") && H.length > 0 && html`<section><div class="psec"><h3>Hub apps</h3><span>${H.length}</span></div><div class="appgrid">${H.map((a) => tile(null, a.runnable ? "Ready" : a.missing_models.length ? `Needs ${a.missing_models.length} file${a.missing_models.length > 1 ? "s" : ""}` : "Needs nodes", a.title, `${a.inputs} input${a.inputs === 1 ? "" : "s"}, ${a.outputs} output${a.outputs === 1 ? "" : "s"}`, () => open(a.id), a.id))}</div></section>`}
    ${!all && !err && html`<p class="small">Loading every graph...</p>`}${all > 0 && !G.length && !R.length && !F.length && !H.length && html`<p class="small">Nothing matches. Try fewer words.</p>`}
    ${graphRow && html`<${GraphPanel} row=${graphRow} onClose=${() => setGraphRow(null)}/>`}</div>`; }
  return html`<div class="lk ap-page"><button class="btn small ap-back" onClick=${() => setApp(null)}>All apps</button><${Head}>${app.title}<//>
    <div class="ap-layout"><div class="card"><h3>Inputs</h3>
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
