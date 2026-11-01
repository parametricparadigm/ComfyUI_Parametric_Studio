import { useState, useEffect, useRef, useMemo } from "preact/hooks";
import { html } from "./common.js";
import { fitDistance } from "./fit_distance.js";

export { fitDistance };

const reducedMotion = () => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;

// height: pixels, or any CSS length. spin: start turning (never under reduced motion). grid: a floor grid in real metres. lens: { pos, look, lens_mm, sensor_mm } looks through a shot's camera, in the shot's Blender metres.
export function Viewer3D({ url, height = 420, spin = false, grid = false, background = 0x222222, label = "3D view", lens = null }) {
  const containerRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [autoRotate, setAutoRotate] = useState(() => spin && !reducedMotion());
  const [cell, setCell] = useState(0);
  const controlsRef = useRef(null);
  const lensRef = useRef(null);
  lensRef.current = lens;

  useEffect(() => {
    let renderer;
    let scene;
    let camera;
    let controls;
    let animationId;
    let resizeObserver;
    let disposed = false;
    const disposables = [];

    async function init() {
      try {
        const THREE = await import('three');
        const { GLTFLoader } = await import('three/addons/loaders/GLTFLoader.js');
        const { OrbitControls } = await import('three/addons/controls/OrbitControls.js');

        if (disposed) return;

        const container = containerRef.current;
        if (!container) return;

        const canvas = document.createElement('canvas');
        canvas.tabIndex = 0;
        canvas.setAttribute('aria-label', `${label}. Arrow keys turn it, plus and minus zoom.`);
        canvas.addEventListener('keydown', (e) => {
          if (!controls || !controls.enabled) return;
          const turn = { ArrowLeft: -0.14, ArrowRight: 0.14 }[e.key] || 0, tilt = { ArrowUp: -0.1, ArrowDown: 0.1 }[e.key] || 0, zoom = { '+': 0.88, '=': 0.88, '-': 1.14 }[e.key] || 1;
          if (!turn && !tilt && zoom === 1) return;
          e.preventDefault();
          const off = camera.position.clone().sub(controls.target), sph = new THREE.Spherical().setFromVector3(off);
          sph.theta += turn; sph.phi = Math.min(Math.PI - 0.05, Math.max(0.05, sph.phi + tilt)); sph.radius *= zoom;
          camera.position.copy(controls.target).add(off.setFromSpherical(sph));
        });
        container.appendChild(canvas);

        renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.setSize(container.clientWidth, container.clientHeight);

        scene = new THREE.Scene();
        scene.background = new THREE.Color(background);

        camera = new THREE.PerspectiveCamera(50, container.clientWidth / container.clientHeight, 0.1, 1000);

        const hemiLight = new THREE.HemisphereLight(0xffffff, 0x444444, 1);
        scene.add(hemiLight);

        const dirLight = new THREE.DirectionalLight(0xffffff, 1);
        dirLight.position.set(5, 5, 5);
        scene.add(dirLight);

        const loader = new GLTFLoader();
        loader.load(
          url,
          (gltf) => {
            if (disposed) return;
            const model = gltf.scene;
            model.traverse((o) => { if (/-(colonly|convcolonly|col)(_\d+)?$/i.test(o.name || "")) o.visible = false; });   // a game engine's collision shapes, not something to look at
            
            // Frame what the asset is: scenery out to the horizon (a place's backdrop and sea) stays in view but does not set the camera's distance.
            const solid = new THREE.Box3(); let scenery = false;
            model.traverse((o) => { if (!o.isMesh) return; const named = (s) => /^(backdrop|sea)/i.test((s && s.name) || ""); if (named(o) || named(o.parent)) scenery = true; else if (o.visible && o.parent.visible) solid.expandByObject(o); });
            const box = scenery && !solid.isEmpty() ? solid : new THREE.Box3().setFromObject(model);
            const center = box.getCenter(new THREE.Vector3());
            model.position.sub(center);
            
            scene.add(model);

            const size = box.getSize(new THREE.Vector3());
            if (grid) {
              const longest = Math.max(size.x, size.z, 0.5), step = longest > 25 ? 5 : longest > 6 ? 1 : longest > 1.5 ? 0.5 : 0.1, span = Math.ceil(longest * 1.5 / step);
              const floor = new THREE.GridHelper(span * step, span, 0xf5c518, 0x5c5a3c);
              floor.position.y = box.min.y - center.y;
              floor.material.transparent = true; floor.material.opacity = 0.55;
              scene.add(floor); setCell(step);
            }
            const boxData = {
              min: [box.min.x, box.min.y, box.min.z],
              max: [box.max.x, box.max.y, box.max.z]
            };
            
            const distance = fitDistance(boxData, 50, container.clientWidth / container.clientHeight);
            camera.position.set(0, scenery ? distance * 0.55 : 0, distance);
            camera.lookAt(0, 0, 0);

            controls = new OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.05;
            controls.autoRotate = autoRotate;
            controlsRef.current = controls;

            setLoading(false);

            const animate = () => {
              if (disposed) return;
              animationId = requestAnimationFrame(animate);
              const shot = lensRef.current;
              controls.enabled = !shot;
              if (shot) {
                // Blender's Z-up metres, as the .glb stores them (Y-up), then the same shift that centred the model.
                const toScene = ([x, y, z]) => new THREE.Vector3(x, z, -y).sub(center);
                camera.position.copy(toScene(shot.pos));
                camera.lookAt(toScene(shot.look));
                controls.target.copy(toScene(shot.look));
                const vfov = 2 * Math.atan(((shot.sensor_mm || 36) / 2) / (camera.aspect * (shot.lens_mm || 35))) * 180 / Math.PI;
                if (Math.abs(camera.fov - vfov) > 0.01) { camera.fov = vfov; camera.updateProjectionMatrix(); }
              } else controls.update();
              renderer.render(scene, camera);
            };
            animate();
          },
          undefined,
          (err) => {
            if (disposed) return;
            setError(err.message || "Failed to load model");
            setLoading(false);
          }
        );

        resizeObserver = new ResizeObserver(() => {
          if (disposed || !container) return;
          const w = container.clientWidth;
          const h = container.clientHeight;
          if (w === 0 || h === 0) return;
          camera.aspect = w / h;
          camera.updateProjectionMatrix();
          renderer.setSize(w, h);
        });
        resizeObserver.observe(container);

      } catch (e) {
        if (!disposed) {
          setError(e.message || "Failed to initialize viewer");
          setLoading(false);
        }
      }
    }

    init();

    return () => {
      disposed = true;
      if (animationId) cancelAnimationFrame(animationId);
      if (resizeObserver) resizeObserver.disconnect();
      
      if (scene) {
        scene.traverse((object) => {
          if (object.geometry) {
            object.geometry.dispose();
          }
          if (object.material) {
            if (Array.isArray(object.material)) {
              object.material.forEach(m => m.dispose());
            } else {
              object.material.dispose();
            }
          }
        });
      }
      if (renderer) {
        renderer.dispose();
        if (renderer.domElement && renderer.domElement.parentNode) {
          renderer.domElement.parentNode.removeChild(renderer.domElement);
        }
      }
    };
  }, [url]);

  const toggleRotate = () => {
    const next = !autoRotate;
    setAutoRotate(next);
    if (controlsRef.current) {
      controlsRef.current.autoRotate = next;
    }
  };

  return html`
    <div class="v3d" style="position: relative; width: 100%; height: ${typeof height === "number" ? height + "px" : height}; background: var(--panel); border: 1px solid var(--line); border-radius: 8px; overflow: hidden;">
      <div ref=${containerRef} style="width: 100%; height: 100%;"></div>
      ${loading && html`<div style="position: absolute; top: 10px; left: 10px; color: var(--mut); font-size: 12px;">Loading...</div>`}
      ${error && html`<div class="small" style="position: absolute; top: 10px; left: 10px; color: var(--err);">${error}</div>`}
      ${cell > 0 && html`<div class="v3d-grid">Floor grid: ${cell < 1 ? cell * 100 + " cm" : cell + " m"} squares</div>`}
      ${!lens && html`<button type="button" class="btn small" aria-pressed=${autoRotate} style="position: absolute; bottom: 10px; right: 10px;" onClick=${toggleRotate}>
        ${autoRotate ? "Stop rotating" : "Rotate"}
      </button>`}
    </div>
  `;
}
