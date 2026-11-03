/* Shared pieces for the studio's pages: the numbered strip, the lit render stage, big numbers, honest empty and offline states. The styles live in looks.css. */
import { useEffect, useRef, useState } from "preact/hooks";
import { html, api } from "./common.js";

const calm = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

/* A real render. Video only plays while it is on screen, and never under reduced motion, where the poster stands in. */
export function Media({ src, poster, kind, alt = "", cls = "", eager, still }) {
  const v = useRef(); const isVideo = kind ? kind === "video" : /\.(mp4|webm)$/i.test(src || "");
  useEffect(() => {
    const el = v.current; if (!el || still || !isVideo || typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { const p = el.play(); if (p && p.catch) p.catch(() => {}); } else el.pause(); }, { threshold: 0.15 });
    io.observe(el); return () => io.disconnect();
  }, [src]);
  if (!isVideo || (calm() && poster)) return html`<img class=${cls} src=${isVideo ? poster : src || poster} alt=${alt} loading=${eager ? "eager" : "lazy"} onError=${(e) => { e.target.style.visibility = "hidden"; }}/>`;
  /* still: the chosen frame stays up, and the clip only plays while a pointer is on it */
  if (still) return html`<video key=${src} class=${cls} src=${src} poster=${poster} muted loop playsinline preload="none" aria-label=${alt || undefined} onMouseEnter=${(e) => { const p = e.currentTarget.play(); if (p && p.catch) p.catch(() => {}); }} onMouseLeave=${(e) => e.currentTarget.load()}></video>`;
  if (calm()) return html`<video class=${cls} src=${src} muted playsinline preload="metadata" aria-label=${alt || undefined}></video>`;
  return html`<video key=${src} ref=${v} class=${cls} src=${src} poster=${poster} muted loop playsinline preload=${poster ? "none" : "metadata"} aria-label=${alt || undefined}></video>`;
}

/* The numbered tab strip. items: { k, b, s }. */
export const Strip = ({ label, items, value, onPick }) => html`<nav class="lk-strip" aria-label=${label} style=${{ "--n": items.length }}><ol>${items.map((x, i) => html`<li key=${x.k}><button type="button" aria-pressed=${value === x.k} onClick=${() => onPick(x.k)}><i>${i + 1}</i><span><b>${x.b}</b>${x.s && html`<small>${x.s}</small>`}</span></button></li>`)}</ol></nav>`;

/* The lit stage: one big render and a rack to change it. items: { id, src, poster, title, sub, kicker, alt }. Stays dark in both themes. */
export function Stage({ items, label, note, children }) {
  const [at, setAt] = useState(0), [playing, setPlaying] = useState(false); const list = (items || []).filter(Boolean); const cur = list[Math.min(at, list.length - 1)];
  if (!cur) return null;
  return html`<section class="lk-stage film" aria-label=${label}>
    <figure class="lk-stagepic">${cur.still && playing ? html`<video key=${cur.src} src=${cur.src} poster=${cur.poster} autoplay loop muted playsinline aria-label=${cur.alt || cur.title}></video>` : html`<${Media} src=${cur.still ? cur.poster : cur.src} poster=${cur.poster} kind=${cur.still ? "image" : cur.kind} alt=${cur.alt || cur.title} eager/>`}
      ${cur.still && html`<button type="button" class="btn small lk-play" aria-pressed=${playing} onClick=${() => setPlaying(!playing)}>${playing ? "Show the still" : "Play the clip"}</button>`}
      <figcaption>${cur.kicker && html`<span class="lk-tag">${cur.kicker}</span>`}<b>${cur.title}</b>${cur.sub && html`<small>${cur.sub}</small>`}</figcaption></figure>
    ${(list.length > 1 || children) && html`<div class="lk-stageside">${children}${list.length > 1 && html`<ul class="lk-rack">${list.map((x, i) => html`<li key=${x.id}><button type="button" aria-pressed=${x === cur} onClick=${() => { setAt(i); setPlaying(false); }}>${x.kind !== "video" && (x.poster || !/\.(mp4|webm)$/i.test(x.src)) || (x.kind === "video" && x.poster) ? html`<img src=${x.poster || x.src} alt="" loading="lazy"/>` : html`<video src=${x.src} muted playsinline preload="metadata" aria-hidden="true"></video>`}<span><b>${x.title}</b>${x.sub && html`<small>${x.sub}</small>`}</span></button></li>`)}</ul>`}</div>`}
    ${note && html`<p class="lk-stagenote">${note}</p>`}
  </section>`;
}

/* Big numbers that come from the page's own data. items: [value, label]. */
export const Stats = ({ items }) => html`<dl class="lk-stats">${items.map(([v, l]) => html`<div key=${l}><dd>${v}</dd><dt>${l}</dt></div>`)}</dl>`;

/* A numbered heading for a section. */
export const Head = ({ n, id, children, sub }) => html`<header class="lk-head"><h2 id=${id} tabindex=${id ? "-1" : undefined}>${n != null && html`<i>${n}</i>`}${children}</h2>${sub && html`<p>${sub}</p>`}</header>`;

/* An empty state with a real render behind it and a next step. The note says whose render it is. */
export const Empty = ({ art, poster, kicker, title, note, children }) => html`<section class="lk-empty film">
  ${art && html`<div class="lk-emptypic"><${Media} src=${art} poster=${poster} eager/></div>`}
  <div class="lk-emptytext">${kicker && html`<span class="lk-kick">${kicker}</span>`}<h2>${title}</h2>${children}${note && html`<p class="lk-emptynote">${note}</p>`}</div></section>`;

/* What is true right now when ComfyUI cannot be reached. */
export const Offline = ({ health, children }) => (health && !health.comfy && health.edition !== "demo" ? html`<div class="lk-warn" role="status"><b>ComfyUI is not reachable${health.comfy_url ? ` at ${health.comfy_url}` : ""}</b><p>${children}</p></div>` : null);

/* The same check the shell runs. Refreshes on its own, so a page recovers when ComfyUI comes back. */
export function useHealth() {
  const [health, setHealth] = useState(null);
  useEffect(() => { const f = () => api("/api/health").then(setHealth).catch(() => setHealth({ comfy: false })); f(); const t = setInterval(f, 15000); return () => clearInterval(t); }, []);
  return health;
}
