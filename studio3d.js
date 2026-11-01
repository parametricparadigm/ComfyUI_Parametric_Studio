/* The 3D page: a dark stage with real lighting, one real mesh on a turntable, a shelf to swap between meshes, four ways to look at it, and readouts measured from the file itself. Three.js is loaded only here, on demand. */
import { useEffect, useRef, useState } from "preact/hooks";
import { html, api } from "./common.js";
import { fitDistance } from "./fit_distance.js";

const calm = () => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;
const MODES = [["textured", "Textured"], ["clay", "Clay"], ["wire", "Wireframe"], ["normals", "Normals"]];
const mb = (b) => (b >= 1048576 ? (b / 1048576).toFixed(1) + " MB" : Math.round(b / 1024) + " KB");
const metres = (n) => (n >= 100 ? Math.round(n) : n >= 10 ? n.toFixed(1) : n.toFixed(2));
const count = (n) => (n >= 1e6 ? (n / 1e6).toFixed(1) + "M" : n >= 1e3 ? (n / 1e3).toFixed(1) + "k" : String(n));

function Stage({ item, mode, spin, onLoaded, onFail }) {
  const box = useRef(null), live = useRef({});
  useEffect(() => {
    let gone = false, raf = 0, ro = null; const host = box.current, st = live.current; const bin = [];
    (async () => {
      try {
        const THREE = await import("three");
        const { GLTFLoader } = await import("three/addons/loaders/GLTFLoader.js");
        const { OrbitControls } = await import("three/addons/controls/OrbitControls.js");
        if (gone || !host) return;
        const canvas = document.createElement("canvas"); canvas.tabIndex = 0; canvas.setAttribute("aria-label", `3D view of ${item.name}. Arrow keys turn it, plus and minus zoom.`); host.appendChild(canvas);
        const r = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true }); r.setPixelRatio(Math.min(devicePixelRatio, 2)); r.setSize(host.clientWidth, host.clientHeight);
        r.toneMapping = THREE.ACESFilmicToneMapping; r.toneMappingExposure = 1.18; r.shadowMap.enabled = true; r.shadowMap.type = THREE.PCFSoftShadowMap;
        const scene = new THREE.Scene(); scene.background = new THREE.Color(0x060706);
        const cam = new THREE.PerspectiveCamera(38, host.clientWidth / host.clientHeight, 0.01, 4000);
        const gltf = await new GLTFLoader().loadAsync(item.url); if (gone) { r.dispose(); return; }
        const model = gltf.scene; model.traverse((o) => { if (/-(colonly|convcolonly|col)(_\d+)?$/i.test(o.name || "")) o.visible = false; });
        /* a rigged mesh's file bounds are for its rest pose before the bones act, so measure those vertex by vertex */
        model.updateMatrixWorld(true); const solid = new THREE.Box3(), every = new THREE.Box3(); let scenery = false; model.traverse((o) => { if (!o.isMesh || !o.visible) return; every.expandByObject(o, !!o.isSkinnedMesh); const named = (s) => /^(backdrop|sea)/i.test((s && s.name) || ""); if (named(o) || named(o.parent)) scenery = true; else solid.expandByObject(o, !!o.isSkinnedMesh); });
        const bb = scenery && !solid.isEmpty() ? solid : every, size = bb.getSize(new THREE.Vector3()), mid = bb.getCenter(new THREE.Vector3()), big = Math.max(size.x, size.y, size.z) || 1;
        model.position.set(-mid.x, -bb.min.y, -mid.z); const turntable = new THREE.Group(); turntable.add(model); scene.add(turntable);
        let tris = 0, verts = 0; const mats = new Set(); st.meshes = [];
        model.traverse((o) => { if (!o.isMesh) return; o.castShadow = o.receiveShadow = true; const g = o.geometry, p = g.attributes.position; if (!g.attributes.normal) { g.computeVertexNormals(); (Array.isArray(o.material) ? o.material : [o.material]).forEach((m) => { m.flatShading = false; m.needsUpdate = true; }); } verts += p ? p.count : 0; tris += g.index ? g.index.count / 3 : p ? p.count / 3 : 0; (Array.isArray(o.material) ? o.material : [o.material]).forEach((m) => mats.add(m)); st.meshes.push({ o, orig: o.material }); });
        const hasColour = [...mats].some((m) => m.map || m.vertexColors || (m.color && m.color.getHex() !== 0xffffff));
        /* the light: warm key from high left, cold green rim behind, a low fill so nothing goes fully black */
        scene.add(new THREE.HemisphereLight(0x8fa596, 0x0a0806, 0.75));
        const key = new THREE.SpotLight(0xffe2a6, 0, big * 9, 0.62, 0.55, 0); key.intensity = 5.4; key.position.set(-big * 1.5, big * 2.6, big * 1.8); key.target.position.set(0, size.y * 0.4, 0); key.castShadow = true; key.shadow.mapSize.set(2048, 2048); key.shadow.radius = 6; key.shadow.bias = -0.0004; key.shadow.camera.near = big * 0.2; key.shadow.camera.far = big * 8; scene.add(key, key.target);
        const rim = new THREE.DirectionalLight(0x8fe8bf, 1.1); rim.position.set(big * 1.6, big * 1.1, -big * 2.2); scene.add(rim);
        const fill = new THREE.DirectionalLight(0xbcd2ff, 0.8); fill.position.set(big * 2, big * 0.4, big * 2); scene.add(fill);
        const R = big * 3.2, floorGeo = new THREE.CircleGeometry(R, 64), floorMat = new THREE.MeshStandardMaterial({ color: 0x0d100e, roughness: 0.78, metalness: 0.25 }); const floor = new THREE.Mesh(floorGeo, floorMat); floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);
        scene.fog = new THREE.Fog(0x060706, big * 3.2, big * 7);
        const ring = new THREE.Mesh(new THREE.RingGeometry(big * 0.92, big * 0.935, 96), new THREE.MeshBasicMaterial({ color: 0xf5c518, transparent: true, opacity: 0.45 })); ring.rotation.x = -Math.PI / 2; ring.position.y = big * 0.002; scene.add(ring);
        bin.push(floorGeo, floorMat, ring.geometry, ring.material);
        const clay = new THREE.MeshStandardMaterial({ color: 0xb9b6a6, roughness: 0.82, metalness: 0, flatShading: false }), wire = new THREE.MeshBasicMaterial({ color: 0xf5c518, wireframe: true, transparent: true, opacity: tris > 40000 ? 0.16 : 0.8, depthWrite: false }), normals = new THREE.MeshNormalMaterial(); bin.push(clay, wire, normals);
        st.apply = (m) => { for (const x of st.meshes) x.o.material = m === "clay" ? clay : m === "wire" ? wire : m === "normals" ? normals : x.orig; };
        st.apply(mode);
        const d = fitDistance({ min: [-size.x / 2, 0, -size.z / 2], max: [size.x / 2, size.y, size.z / 2] }, cam.fov, cam.aspect) * 1.12; const look = new THREE.Vector3(0, size.y * 0.45, 0);
        cam.position.set(d * 0.62, Math.max(size.y * 0.75, d * 0.34), d * 0.78); cam.far = Math.max(d * 12, big * 30); cam.near = Math.max(d / 400, 0.001); cam.updateProjectionMatrix();
        const shift = () => { const w = host.clientWidth, h = host.clientHeight; if (w / h > 1.35) cam.setViewOffset(w, h, -w * 0.12, 0, w, h); else cam.clearViewOffset(); }; shift();
        const c = new OrbitControls(cam, canvas); c.target.copy(look); c.enableDamping = true; c.dampingFactor = 0.06; c.maxPolarAngle = Math.PI * 0.495; st.controls = c;
        canvas.addEventListener("keydown", (e) => { const turn = { ArrowLeft: -0.14, ArrowRight: 0.14 }[e.key] || 0, tilt = { ArrowUp: -0.1, ArrowDown: 0.1 }[e.key] || 0, zoom = { "+": 0.88, "=": 0.88, "-": 1.14 }[e.key] || 1; if (!turn && !tilt && zoom === 1) return; e.preventDefault(); const off = cam.position.clone().sub(c.target), s = new THREE.Spherical().setFromVector3(off); s.theta += turn; s.phi = Math.min(Math.PI * 0.495, Math.max(0.05, s.phi + tilt)); s.radius *= zoom; cam.position.copy(c.target).add(off.setFromSpherical(s)); });
        ro = new ResizeObserver(() => { if (!host.clientWidth) return; r.setSize(host.clientWidth, host.clientHeight); cam.aspect = host.clientWidth / host.clientHeight; shift(); cam.updateProjectionMatrix(); }); ro.observe(host);
        /* the model turns, not the camera, so the light stays where it was set */
        st.spin = spin; let last = performance.now();
        const tick = (t = performance.now()) => { if (gone) return; raf = requestAnimationFrame(tick); if (st.spin) turntable.rotation.y += Math.min(t - last, 100) * 0.00028; last = t; c.update(); r.render(scene, cam); }; tick();
        onLoaded({ tris: Math.round(tris), verts, materials: mats.size, size: [size.x, size.y, size.z], hasColour, thumb: canvas.toDataURL("image/jpeg", 0.6) });
        bin.push(r, c); st.dispose = () => { scene.traverse((o) => { if (o.geometry) o.geometry.dispose(); }); mats.forEach((m) => { Object.values(m).forEach((v) => { if (v && v.isTexture) v.dispose(); }); m.dispose(); }); };
      } catch (e) { if (!gone) onFail(String((e && e.message) || e)); }
    })();
    return () => { gone = true; cancelAnimationFrame(raf); if (ro) ro.disconnect(); if (st.dispose) st.dispose(); bin.forEach((x) => x.dispose && x.dispose()); st.apply = null; st.controls = null; st.dispose = null; while (host.firstChild) host.removeChild(host.firstChild); };
  }, [item.url]);
  useEffect(() => { if (live.current.apply) live.current.apply(mode); }, [mode]);
  useEffect(() => { live.current.spin = spin; }, [spin]);
  return html`<div class="v3x-canvas" ref=${box}></div>`;
}

export function Studio3D() {
  const [samples, setSamples] = useState([]), [mine, setMine] = useState([]), [cur, setCur] = useState(null), [mode, setMode] = useState("textured"), [spin, setSpin] = useState(!calm()), [info, setInfo] = useState(null), [loading, setLoading] = useState(true), [err, setErr] = useState(""), [listErr, setListErr] = useState(""), [thumbs, setThumbs] = useState({});
  useEffect(() => {
    fetch("mesh_art/index.json").then((r) => (r.ok ? r.json() : [])).then((d) => { const rows = d.map((x) => ({ ...x, url: "mesh_art/" + x.file, thumb: "mesh_art/" + x.thumb, sample: true })); setSamples(rows); setCur((c) => c || rows[0] || null); }).catch(() => {});
    api("/api/models3d").then((d) => setMine([...(d.items || []).map((m) => ({ id: m.url, url: m.url, bytes: m.bytes, name: m.path.split("/").pop(), made: "In your output folder" })), ...(d.family_items || []).map((m) => ({ id: m.url, url: m.url, bytes: m.bytes, name: m.path.split("/").pop(), made: `From ${m.family}'s own ComfyUI` }))])).catch((e) => setListErr(e.message));
  }, []);
  const pick = (x) => { if (cur && x.id === cur.id) return; setCur(x); setInfo(null); setErr(""); setLoading(true); };
  const shelf = [...mine, ...samples];
  if (!cur) return html`<div class="lk v3-page"><p class="small">${listErr || "Reading the shelf..."}</p></div>`;
  const s = info && info.size;
  return html`<div class="lk v3-page">
    <section class="v3x film" aria-label=${"Stage: " + cur.name}>
      <${Stage} key=${cur.id} item=${cur} mode=${mode} spin=${spin} onLoaded=${(d) => { setInfo(d); setLoading(false); setThumbs((t) => ({ ...t, [cur.id]: d.thumb })); }} onFail=${(m) => { setErr(m); setLoading(false); }}/>
      ${err && html`<div class="v3x-fail" role="alert">${cur.thumb && html`<img src=${cur.thumb} alt=""/>`}<p><b>This model could not be shown.</b> ${err}</p></div>`}
      ${loading && html`<p class="v3x-load" role="status">Loading ${cur.name}...</p>`}
      <div class="v3x-title"><span class="lk-tag">${cur.sample ? "Our test build" : "Yours"}</span><h2>${cur.name}</h2><p>${cur.made}</p></div>
      <div class="v3x-modes" role="group" aria-label="View mode">${MODES.map(([k, l]) => html`<button key=${k} type="button" aria-pressed=${mode === k} onClick=${() => setMode(k)}>${l}</button>`)}<button type="button" class="v3x-spin" aria-pressed=${spin} onClick=${() => setSpin(!spin)}>${spin ? "Stop turning" : "Turn it"}</button></div>
    </section>
    <p class="lk-plain v3x-scale">Drag to orbit, scroll to zoom, or focus the stage and use the arrow keys.</p>
    <dl class="v3x-read">
      <div><dd>${s ? `${metres(s[0])} × ${metres(s[1])} × ${metres(s[2])}` : "..."}</dd><dt>metres in the file, wide × tall × deep</dt></div>
      ${cur.scale_m && html`<div><dd>${cur.scale_m} m</dd><dt>size it was built to, from its build record</dt></div>`}
      <div><dd>${info ? count(info.tris) : "..."}</dd><dt>triangles</dt></div>
      <div><dd>${info ? count(info.verts) : "..."}</dd><dt>vertices</dt></div>
      <div><dd>${info ? info.materials : "..."}</dd><dt>${info && info.materials === 1 ? "material" : "materials"}</dt></div>
      ${(cur.bytes || cur.file_bytes) && html`<div><dd>${mb(cur.bytes || cur.file_bytes)}</dd><dt>file size</dt></div>`}
    </dl>
    ${!cur.scale_m && html`<p class="lk-plain v3x-scale">glTF files count in metres, but a model made from a single picture does not know its real size, so read these as the file's own units.</p>`}
    ${info && !info.hasColour && mode === "textured" && html`<p class="lk-plain v3x-scale">This file has no texture or colour of its own, so Textured looks plain.</p>`}
    <section aria-label="Shelf"><div class="v3x-shelfhead"><h3>The shelf</h3><p>${mine.length ? `${mine.length} made on this machine, ${samples.length} of our test builds.` : `No generated .glb files yet, so these are our own ${samples.length} test builds, not your work.`}</p></div>
      <ul class="v3x-shelf">${shelf.map((x) => html`<li key=${x.id}><button type="button" aria-pressed=${x.id === cur.id} onClick=${() => pick(x)}><span class="v3x-thumb">${thumbs[x.id] || x.thumb ? html`<img src=${thumbs[x.id] || x.thumb} alt="" loading="lazy"/>` : html`<i aria-hidden="true">3D</i>`}</span><b>${x.name}</b><small>${x.sample ? "Our test build" : x.made}${x.bytes ? `, ${mb(x.bytes)}` : ""}</small></button></li>`)}</ul>
      ${listErr && html`<p class="small" style="color:var(--err)" role="alert">Your own models could not be listed: ${listErr}</p>`}</section>
    <section class="v3x-make"><h3>Make one to look at</h3><div class="lk-acts"><a class="btn" href="#worldkit">World Kit</a><a class="btn" href="#processes">Photo to 3D in Processes</a><a class="btn" href="#virtualset">Virtual Set</a><a class="btn" href="#families">3D families</a></div></section>
  </div>`;
}
