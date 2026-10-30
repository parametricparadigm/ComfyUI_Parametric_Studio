/* 3D layer: a live three.js "parametric core" hero (gold wireframe + emerald core + orbit rings + particle field, pointer parallax) and pointer-driven 3D tilt with specular glare on cards. Pauses off-screen and when the tab is hidden; a still frame under reduced motion. */
import { useEffect, useRef } from "preact/hooks";
import { html } from "./common.js";
export function Hero3D() {
  const ref = useRef(null);
  useEffect(() => {
    let alive = true, cleanup = () => {};
    (async () => {
      const THREE = await import("three"); if (!alive || !ref.current) return;
      const el = ref.current, reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
      const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true }); renderer.setPixelRatio(Math.min(devicePixelRatio, 2)); el.appendChild(renderer.domElement);
      const scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(40, 1, 0.1, 100); cam.position.set(0, 0, 6.4);
      const gold = 0xd4af37, green = 0x2ecc71, group = new THREE.Group(); scene.add(group);
      const ico = new THREE.Mesh(new THREE.IcosahedronGeometry(1.55, 1), new THREE.MeshBasicMaterial({ color: gold, wireframe: true, transparent: true, opacity: 0.7 })); group.add(ico);
      const core = new THREE.Mesh(new THREE.OctahedronGeometry(0.82, 0), new THREE.MeshStandardMaterial({ color: green, emissive: green, emissiveIntensity: 0.65, metalness: 0.4, roughness: 0.25 })); group.add(core);
      const mkRing = (r, c, rx, ry) => { const m = new THREE.Mesh(new THREE.TorusGeometry(r, 0.014, 8, 180), new THREE.MeshBasicMaterial({ color: c, transparent: true, opacity: 0.65 })); m.rotation.set(rx, ry, 0); group.add(m); return m; };
      const r1 = mkRing(2.35, green, 1.2, 0.2), r2 = mkRing(2.9, gold, 0.4, 1.1);
      const N = 380, pos = new Float32Array(N * 3);
      for (let i = 0; i < N; i++) { const rad = 3.4 + Math.random() * 2.4, th = Math.random() * 6.283, ph = Math.acos(2 * Math.random() - 1); pos.set([rad * Math.sin(ph) * Math.cos(th), rad * Math.sin(ph) * Math.sin(th), rad * Math.cos(ph)], i * 3); }
      const pg = new THREE.BufferGeometry(); pg.setAttribute("position", new THREE.BufferAttribute(pos, 3)); const pts = new THREE.Points(pg, new THREE.PointsMaterial({ color: gold, size: 0.035, transparent: true, opacity: 0.8 })); scene.add(pts);
      scene.add(new THREE.AmbientLight(0xffffff, 0.45)); const l1 = new THREE.PointLight(gold, 40, 20); l1.position.set(3, 3, 4); const l2 = new THREE.PointLight(green, 32, 20); l2.position.set(-3, -2, 3); scene.add(l1, l2);
      const size = () => { const w = el.clientWidth || 400, h = el.clientHeight || 260; renderer.setSize(w, h, false); cam.aspect = w / h; cam.updateProjectionMatrix(); };
      const ro = new ResizeObserver(size); ro.observe(el); size();
      let tx = 0, ty = 0, vis = true, raf = 0; const io = new IntersectionObserver((e) => { vis = e[0].isIntersecting; }); io.observe(el);
      const move = (e) => { tx = (e.clientX / innerWidth - 0.5) * 0.9; ty = (e.clientY / innerHeight - 0.5) * 0.6; }; addEventListener("pointermove", move, { passive: true });
      const frame = (t) => {
        if (reduce) { renderer.render(scene, cam); return; }
        raf = requestAnimationFrame(frame); if (!vis || document.hidden) return;
        const s = t * 0.001; ico.rotation.set(s * 0.18, s * 0.25, 0); core.rotation.set(-s * 0.4, s * 0.55, 0); r1.rotation.z = s * 0.3; r2.rotation.z = -s * 0.22; pts.rotation.y = s * 0.04;
        group.rotation.y += (tx - group.rotation.y) * 0.04; group.rotation.x += (ty - group.rotation.x) * 0.04; core.scale.setScalar(1 + Math.sin(s * 1.6) * 0.05); renderer.render(scene, cam);
      };
      raf = requestAnimationFrame(frame);
      cleanup = () => { cancelAnimationFrame(raf); ro.disconnect(); io.disconnect(); removeEventListener("pointermove", move); [ico, core, r1, r2, pts].forEach((m) => { m.geometry.dispose(); m.material.dispose(); }); renderer.dispose(); renderer.domElement.remove(); };
    })().catch(() => {});
    return () => { alive = false; cleanup(); };
  }, []);
  return html`<div class="hero3d" ref=${ref} aria-hidden="true"></div>`;
}
/* pointer-driven 3D tilt + glare, by event delegation on any element with .tilt3d (no per-card listeners) */
export function installTilt() {
  if (matchMedia("(prefers-reduced-motion: reduce)").matches || matchMedia("(hover: none)").matches) return;
  let cur = null;
  const reset = (n) => { if (n) { n.style.setProperty("--rx", "0deg"); n.style.setProperty("--ry", "0deg"); n.style.setProperty("--gl", "0"); } };
  addEventListener("pointermove", (e) => {
    const n = e.target.closest && e.target.closest(".tilt3d"); if (cur && cur !== n) reset(cur); cur = n; if (!n) return;
    const r = n.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
    n.style.setProperty("--ry", ((x - 0.5) * 9).toFixed(2) + "deg"); n.style.setProperty("--rx", ((0.5 - y) * 9).toFixed(2) + "deg"); n.style.setProperty("--gx", (x * 100).toFixed(1) + "%"); n.style.setProperty("--gy", (y * 100).toFixed(1) + "%"); n.style.setProperty("--gl", "1");
  }, { passive: true });
  document.addEventListener("pointerleave", () => reset(cur), true);
}
