/* The Create page's media layer: a draggable 3D wall of real renders (three.js video textures on three counter-rotating curved rows), the goal deck, and the masonry of work. All media is what this studio actually rendered, with its measured time and VRAM. */
import { useEffect, useRef, useState } from "preact/hooks";
import { html } from "./common.js";

export const FLAGSHIPS = ["recast", "director", "reshoot", "vfx_ltx", "product"];
const UNPROVEN = ["orbit360", "reshoot_wan"];   // graphs validate but have not rendered here yet
let cache = null;
export function useShowcase() {
  const [items, setItems] = useState(cache || []);
  useEffect(() => { if (cache) return; fetch("showcase/showcase.json").then((r) => (r.ok ? r.json() : [])).then((d) => { cache = d; setItems(d); }).catch(() => {}); }, []);
  return items;
}

/* cover-fit a texture on a panel; the inside of a cylinder mirrors U, so repeat.x is negative */
function coverFit(tex, srcA, panelA) {
  const rx = srcA > panelA ? panelA / srcA : 1, ry = srcA > panelA ? 1 : srcA / panelA;
  tex.repeat.set(-rx, ry); tex.offset.set((1 + rx) / 2, (1 - ry) / 2);
}

export function RingHero({ items, onPick }) {
  const ref = useRef(null); const pickRef = useRef(onPick); pickRef.current = onPick;
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    const visual = items.filter((x) => x.kind !== "audio"); if (!visual.length || !ref.current) return;
    let alive = true, cleanup = () => {};
    (async () => {
      let THREE; try { THREE = await import("three"); } catch { setFailed(true); return; }
      if (!alive || !ref.current) return;
      const el = ref.current, reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
      let renderer; try { renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true }); } catch { setFailed(true); return; }
      renderer.setPixelRatio(Math.min(devicePixelRatio, 1.75)); renderer.outputColorSpace = THREE.SRGBColorSpace; el.appendChild(renderer.domElement);
      const scene = new THREE.Scene(); scene.fog = new THREE.Fog(0x060807, 6.5, 13);
      const cam = new THREE.PerspectiveCamera(52, 2, 0.1, 40); cam.position.set(0, 0, 0.6);
      const R = 7, N = 11, THETA = (Math.PI * 2) / N, GAP = 0.965, ARC = R * THETA * GAP, H = ARC * 0.58, PA = ARC / H;
      const vids = [], maxVideos = 8; let vcount = 0; const loader = new THREE.TextureLoader(); loader.setCrossOrigin("anonymous");
      const texFor = (it) => {
        const a = (it.w || 16) / (it.h || 9); let t;
        if (it.kind === "video" && vcount < maxVideos) {
          vcount++; const v = document.createElement("video"); v.src = it.src; v.muted = true; v.loop = true; v.playsInline = true; v.preload = "auto"; v.crossOrigin = "anonymous"; v.play().catch(() => {}); vids.push(v);
          t = new THREE.VideoTexture(v);
        } else t = loader.load(it.poster || it.src);
        t.colorSpace = THREE.SRGBColorSpace; t.minFilter = THREE.LinearFilter; t.generateMipmaps = false; coverFit(t, a, PA); return t;
      };
      const texCache = new Map(); const tex = (it) => { if (!texCache.has(it.id)) texCache.set(it.id, texFor(it)); return texCache.get(it.id); };
      const videosFirst = [...visual].sort((a, b) => (b.kind === "video") - (a.kind === "video"));
      const rows = [], pickable = []; let idx = 0;
      const seq = [0, 1, 2].map(() => []); videosFirst.forEach((it, i) => seq[i % 3].push(it));
      [[0, 0.018], [H + 0.16, -0.012], [-(H + 0.16), -0.012]].forEach(([y, speed], r) => {
        const g = new THREE.Group(); g.position.y = y; g.rotation.y = r * 0.4; scene.add(g); rows.push({ g, speed });
        const list = seq[r].length ? seq[r] : visual;
        for (let i = 0; i < N; i++) {
          const it = list[(i + idx) % list.length], ts = i * THETA - (THETA * GAP) / 2;
          const panel = new THREE.Mesh(new THREE.CylinderGeometry(R, R, H, 14, 1, true, ts, THETA * GAP), new THREE.MeshBasicMaterial({ map: tex(it), side: THREE.BackSide })); panel.userData.item = it; g.add(panel); pickable.push(panel);
          const edge = new THREE.Mesh(new THREE.CylinderGeometry(R + 0.03, R + 0.03, H + 0.05, 14, 1, true, ts - 0.004, THETA * GAP + 0.008), new THREE.MeshBasicMaterial({ color: 0xf2c230, transparent: true, opacity: 0.32, side: THREE.BackSide })); g.add(edge);
        }
        idx += 3;
      });
      const N2 = 260, pos = new Float32Array(N2 * 3); for (let i = 0; i < N2; i++) { const th = Math.random() * 6.283, rad = 1.6 + Math.random() * 4.6; pos.set([Math.cos(th) * rad, (Math.random() - 0.5) * 6, Math.sin(th) * rad], i * 3); }
      const pg = new THREE.BufferGeometry(); pg.setAttribute("position", new THREE.BufferAttribute(pos, 3)); const dust = new THREE.Points(pg, new THREE.PointsMaterial({ color: 0xf2c230, size: 0.022, transparent: true, opacity: 0.75, depthWrite: false })); scene.add(dust);
      const size = () => { const w = el.clientWidth || 800, h = el.clientHeight || 420; renderer.setSize(w, h, false); cam.aspect = w / h; cam.updateProjectionMatrix(); }; size(); const ro = new ResizeObserver(size); ro.observe(el);
      let px = 0, py = 0, sx = 0, sy = 0, drag = 0, spin = 0, vel = 0, lastX = 0, down = false, moved = 0; const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
      const onMove = (e) => { const r = el.getBoundingClientRect(); px = (e.clientX - r.left) / r.width - 0.5; py = (e.clientY - r.top) / r.height - 0.5; if (down) { const dx = e.clientX - lastX; lastX = e.clientX; moved += Math.abs(dx); vel = dx * 0.0022; drag += vel; }
        else { ndc.set(px * 2, -py * 2); ray.setFromCamera(ndc, cam); el.style.cursor = ray.intersectObjects(pickable)[0] ? "pointer" : "grab"; } };
      const onDown = (e) => { down = true; moved = 0; lastX = e.clientX; el.setPointerCapture && el.setPointerCapture(e.pointerId); };
      const onUp = (e) => { if (down && moved < 6) { const r = el.getBoundingClientRect(); ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1); ray.setFromCamera(ndc, cam); const hit = ray.intersectObjects(pickable)[0]; if (hit && pickRef.current) pickRef.current(hit.object.userData.item); } down = false; };
      el.addEventListener("pointermove", onMove); el.addEventListener("pointerdown", onDown); el.addEventListener("pointerup", onUp);
      let visible = true, raf = 0; const io = new IntersectionObserver((es) => { visible = es[0].isIntersecting; vids.forEach((v) => (visible ? v.play().catch(() => {}) : v.pause())); }); io.observe(el);
      const loop = () => { raf = requestAnimationFrame(loop); if (!visible || document.hidden) return;
        sx += (px - sx) * 0.05; sy += (py - sy) * 0.05; if (!down) { vel *= 0.94; drag += vel; }
        spin += reduce ? 0 : 1; rows.forEach((r) => { r.g.rotation.y = r.base === undefined ? (r.base = r.g.rotation.y) : r.base + (reduce ? 0 : spin * r.speed * 0.012) + drag; });
        cam.rotation.set(-sy * 0.1, -sx * 0.22, 0); dust.rotation.y += 0.0006; renderer.render(scene, cam); };
      loop();
      cleanup = () => { cancelAnimationFrame(raf); ro.disconnect(); io.disconnect(); el.removeEventListener("pointermove", onMove); el.removeEventListener("pointerdown", onDown); el.removeEventListener("pointerup", onUp); vids.forEach((v) => { v.pause(); v.removeAttribute("src"); v.load(); }); texCache.forEach((t) => t.dispose()); renderer.dispose(); renderer.domElement.remove(); };
    })();
    return () => { alive = false; cleanup(); };
  }, [items]);
  return html`<div class="wall3d" ref=${ref} aria-hidden="true">${failed && html`<div class="wallfallback">${items.filter((x) => x.kind !== "audio").slice(0, 6).map((x) => html`<img src=${x.poster} alt="" loading="lazy"/>`)}</div>`}</div>`;
}

/* a video that only plays while on screen */
export function LiveMedia({ item, cls }) {
  const ref = useRef(null);
  useEffect(() => { const v = ref.current; if (!v || item.kind !== "video" || matchMedia("(prefers-reduced-motion: reduce)").matches) return; const io = new IntersectionObserver((es) => { es[0].isIntersecting ? v.play().catch(() => {}) : v.pause(); }, { threshold: 0.15 }); io.observe(v); return () => io.disconnect(); }, [item && item.id]);
  if (!item) return null;
  return item.kind === "video" ? html`<video key=${item.id} ref=${ref} class=${cls} src=${item.src} poster=${item.poster} muted loop playsinline preload="metadata"></video>` : html`<img key=${item.id} class=${cls} src=${item.poster} alt=${item.prompt} loading="lazy"/>`;
}

export function GoalDeck({ goals, goal, items, onPick }) {
  const list = Object.values(goals).filter((g) => !UNPROVEN.includes(g.id)).sort((a, b) => (FLAGSHIPS.indexOf(b.id) >= 0) - (FLAGSHIPS.indexOf(a.id) >= 0));
  const media = (id) => items.find((x) => x.goal === id && x.kind !== "audio") || (id === "product" ? items.find((x) => x.id === "s_sneaker") : null);
  return html`<div class="gdeck" role="listbox" aria-label="what to make">${list.map((g) => { const m = media(g.id), flag = FLAGSHIPS.indexOf(g.id) >= 0; return html`<button role="option" aria-selected=${goal === g.id} class=${"gcard" + (goal === g.id ? " on" : "") + (flag ? " flag" : "")} onClick=${() => onPick(g.id)}>
    ${m ? html`<${LiveMedia} item=${m} cls="gmedia"/>` : html`<div class="gmedia gblank">${g.kind === "audio" ? "♫" : ""}</div>`}
    <span class="gshade"></span>${flag && html`<span class="gflag">Flagship</span>`}<span class="glic" title=${g.license}>${g.license_class === "open" ? "Apache-2.0" : "Community"}</span>
    <span class="gtext"><b>${g.label}</b><small>${g.tagline}</small></span></button>`; })}</div>`;
}

export function Masonry({ items, goals, onOpen, onRecreate, onGraph }) {
  return html`<div class="masonry">${items.filter((x) => x.kind !== "audio").map((x) => html`<article class="mtile" style=${x.w ? { aspectRatio: `${x.w} / ${x.h}` } : null} onClick=${() => onOpen(x)} tabindex="0" onKeyDown=${(e) => { if (e.key === "Enter") onOpen(x); }}>
    <${LiveMedia} item=${x} cls="mmedia"/>
    <div class="mhover"><p>${x.prompt}</p>
      <div class="mmeta">${goals[x.goal] ? goals[x.goal].family : x.goal}${x.seconds ? ` · ${x.seconds}s` : ""}${x.peak_vram_gib ? ` · ${x.peak_vram_gib} GB` : ""}</div>
      <div class="mbtns"><button class="btn small primary" onClick=${(e) => { e.stopPropagation(); onRecreate(x); }}>Recreate</button><button class="btn small" onClick=${(e) => { e.stopPropagation(); onGraph(x); }}>Open the graph</button></div></div>
  </article>`)}</div>`;
}

/* upload zone: click or drop a file; shows what is loaded; optional one-click example so anyone can try a flagship with no footage of their own */
export function Drop({ label, accept, file, onFile, example, hint }) {
  const ref = useRef(null); const [over, setOver] = useState(false); const [busy, setBusy] = useState(false);
  const take = async (f) => { if (!f) return; setBusy(true); try { await onFile(f); } finally { setBusy(false); } };
  const tryExample = async (e) => { e.stopPropagation(); setBusy(true); try { const r = await fetch(example.src); const b = await r.blob(); await onFile(new File([b], example.src.split("/").pop(), { type: b.type })); } finally { setBusy(false); } };
  const isVid = file && /\.(mp4|webm|mov|mkv)$/i.test(file.name);
  return html`<div class=${"drop" + (over ? " over" : "") + (file ? " has" : "")} role="button" tabindex="0" aria-label=${label} onClick=${() => ref.current.click()} onKeyDown=${(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); ref.current.click(); } }}
    onDragOver=${(e) => { e.preventDefault(); setOver(true); }} onDragLeave=${() => setOver(false)} onDrop=${(e) => { e.preventDefault(); setOver(false); take(e.dataTransfer.files[0]); }}>
    <input ref=${ref} type="file" accept=${accept} hidden onClick=${(e) => e.stopPropagation()} onChange=${(e) => take(e.target.files[0])}/>
    ${file ? (isVid ? html`<video src=${file.url} muted loop autoplay playsinline></video>` : html`<img src=${file.url} alt=${label}/>`) : null}
    <div class="dropt"><b>${label}</b><small>${busy ? "Uploading" : file ? "Click to replace" : (hint || "Click or drop a file")}</small>${!file && example && !busy && html`<button class="btn small" onClick=${tryExample}>Try an example</button>`}</div></div>`;
}
