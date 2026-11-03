/* "The future of generative AI, as we see it": the founders' essay. The words live in future_essay.json so they can be edited without touching code; the figures and totals come from real pipeline runs, so a claim about a run can't drift from the run. */
import { useEffect, useState } from "preact/hooks";
import { html, api } from "./common.js";
import { pageTotals } from "./pipelines_logic.js";
import { FxSkeleton } from "./fx.js";

const fill = (t, n) => String(t || "").replace(/\{(\w+)\}/g, (_, k) => (n[k] == null ? "" : n[k]));
const TAG = { fact: "What we ran", opinion: "Our opinion", plan: "Our plan" };

const figOf = (fig, proofs) => { const p = fig && proofs[fig.pipeline]; const s = p && p.stages.find((x) => x.id === fig.stage); const m = s && s.media.find((x) => x.kind === "video" || x.kind === "image"); return m ? { s, m } : null; };
function Figure({ fig, proofs }) {
  const got = figOf(fig, proofs); if (!got) return null; const { s, m } = got;
  const src = `pipelines/${fig.pipeline}/${m.src}`, poster = m.poster ? `pipelines/${fig.pipeline}/${m.poster}` : undefined;
  return html`<figure class="fu-fig">${m.kind === "video" ? html`<video src=${src} poster=${poster} muted loop playsinline controls preload="none"></video>` : html`<img src=${src} alt=${s.label} loading="lazy"/>`}
    <figcaption>Our render. ${s.model}${s.seed != null ? `, seed ${s.seed}` : ""}. <a href=${"#pipelines/" + fig.pipeline}>The whole chain</a></figcaption></figure>`;
}
const Cites = ({ ids, order }) => (ids || []).length ? html`<sup class="fu-cite">${ids.map((c) => html`<a key=${c} href=${"#future/src-" + c} onClick=${(e) => { e.preventDefault(); const el = document.getElementById("src-" + c); if (el) el.scrollIntoView(); }} aria-label=${"Source " + (order.indexOf(c) + 1)}>[${order.indexOf(c) + 1}]</a>`)}</sup>` : null;

function Block({ b: raw, n, order, proofs, i }) {
  if (raw.big && /\{/.test(raw.big) && !fill(raw.big, n).match(/\d/)) return null;
  const b = n.all_rendered && raw.when_all ? { ...raw, ...raw.when_all } : raw;
  return html`<div class=${"fu-block is-" + b.kind + (figOf(b.figure, proofs) ? " has-fig" : "")}>
    <div class="fu-text">
      <span class="fu-tagrow"><span class=${"fu-tag is-" + b.kind}>${TAG[b.kind]}</span><span class="fu-idx" aria-hidden="true">${String(i + 1).padStart(2, "0")}</span></span>
      ${b.big && html`<p class="fu-big">${fill(b.big, n)}</p>`}
      <h3>${b.head}</h3>
      <p>${fill(b.text, n)}${b.kind !== "opinion" && html`<${Cites} ids=${b.cite} order=${order}/>`}</p>
      ${b.basis && html`<p class="fu-basis"><b>What we base it on:</b> ${fill(b.basis, n)}<${Cites} ids=${b.cite} order=${order}/></p>`}
    </div>
    ${b.figure && html`<${Figure} fig=${b.figure} proofs=${proofs}/>`}
  </div>`;
}

/* The run the essay starts from, stage by stage: the pictures that run really made, each with its model and seed. */
function RunStrip({ id, proof }) {
  const st = ((proof && proof.stages) || []).map((s) => ({ s, m: s.media.find((x) => x.kind === "image") || s.media.find((x) => x.kind === "video" && x.poster) })).filter((x) => x.m).slice(0, 5);
  if (st.length < 2) return null;
  return html`<figure class="fu-run"><ol tabindex="0" aria-label="The first stages of the run">${st.map(({ s, m }, i) => html`<li key=${s.id}><img src=${`pipelines/${id}/${m.kind === "image" ? m.src : m.poster}`} alt=${s.label} loading="lazy"/>${s.status && s.status !== "ok" && html`<em>${s.status === "failed" ? "Failed" : "Flawed"}</em>`}<span><i>${i + 1}</i><b>${s.label}</b><small>${s.model}${s.seed != null ? ` · seed ${s.seed}` : ""}</small></span></li>`)}</ol>
    <figcaption>Our render: the first stages of one run, as it really came out. <a href=${"#pipelines/" + id}>The whole chain</a></figcaption></figure>`;
}

export function Future({ goTab }) {
  const [d, setD] = useState(null), [list, setList] = useState([]), [nums, setNums] = useState({}), [err, setErr] = useState("");
  useEffect(() => { fetch("future_essay.json").then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); }).then(setD).catch((e) => setErr(String(e))); api("/api/pipelines").then((x) => setList(x.pipelines)).catch(() => {}); fetch("future_numbers.json").then((r) => r.json()).then(setNums).catch(() => {}); }, []);
  if (err) return html`<p class="lk-plain" role="alert">The essay didn't load: ${err}</p>`;
  if (!d) return html`<${FxSkeleton} label="Reading the essay."/>`;
  const proofs = {}; list.forEach((p) => { if (p.proof) proofs[p.id] = p.proof; }); const n = { ...nums, ...pageTotals(list) }, order = d.sources.map((s) => s.id), hero = proofs[d.hero.pipeline], fin = hero && hero.final;
  return html`<article class="fu lk">
    <header class="fu-hero film">
      ${fin && fin.kind === "video" && html`<video src=${`pipelines/${d.hero.pipeline}/${fin.src}`} poster=${`pipelines/${d.hero.pipeline}/${fin.poster}`} autoplay=${!matchMedia("(prefers-reduced-motion: reduce)").matches} muted loop playsinline aria-label=${d.hero.alt}></video>`}
      <div><span class="lk-kick">${d.date}</span><p>${d.open}</p></div>
    </header>
    ${d.sections.map((s) => html`<section key=${s.id} class="fu-sec" aria-labelledby=${"fu-" + s.id}>
      <header><span class="fu-no" aria-hidden="true">${s.no}</span><div><h2 id=${"fu-" + s.id}>${s.title}</h2>${s.lede && html`<p class="fu-lede">${s.lede}</p>`}</div></header>
      ${s.id === d.sections[0].id && html`<${RunStrip} id=${d.hero.pipeline} proof=${hero}/>`}
      <div class=${"fu-grid is-" + ((s.blocks[0] || {}).kind || "fact")}>${s.blocks.map((b, i) => html`<${Block} key=${b.head} b=${b} n=${n} order=${order} proofs=${proofs} i=${i}/>`)}</div>
    </section>`)}
    <section class="fu-src" aria-labelledby="fu-src"><h2 id="fu-src">Sources</h2><ol>${d.sources.map((s) => html`<li key=${s.id} id=${"src-" + s.id}>${s.href ? html`<a href=${s.href} target=${s.href.startsWith("#") ? undefined : "_blank"} rel="noopener">${fill(s.label, n)}</a>` : fill(s.label, n)}</li>`)}</ol></section>
    <p class="fu-end"><button class="btn primary" type="button" onClick=${() => goTab("pipelines")}>See every stage of the runs</button></p>
  </article>`;
}
