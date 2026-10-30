import { useState, useEffect, useRef, useMemo } from "preact/hooks";
import { html } from "./common.js";
import { fitDistance } from "./fit_distance.js";

export { fitDistance };

export function Viewer3D({ url, height = 420 }) {
  const containerRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [autoRotate, setAutoRotate] = useState(false);
  const controlsRef = useRef(null);

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
        container.appendChild(canvas);

        renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.setSize(container.clientWidth, container.clientHeight);

        scene = new THREE.Scene();
        scene.background = new THREE.Color(0x222222);

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
            
            const box = new THREE.Box3().setFromObject(model);
            const center = box.getCenter(new THREE.Vector3());
            model.position.sub(center);
            
            scene.add(model);

            const size = box.getSize(new THREE.Vector3());
            const boxData = {
              min: [box.min.x, box.min.y, box.min.z],
              max: [box.max.x, box.max.y, box.max.z]
            };
            
            const distance = fitDistance(boxData, 50, container.clientWidth / container.clientHeight);
            camera.position.set(0, 0, distance);
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
              controls.update();
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
    <div style="position: relative; width: 100%; height: ${height}px; background: var(--panel); border: 1px solid var(--line); border-radius: 8px; overflow: hidden;">
      <div ref=${containerRef} style="width: 100%; height: 100%;"></div>
      ${loading && html`<div style="position: absolute; top: 10px; left: 10px; color: var(--mut); font-size: 12px;">Loading...</div>`}
      ${error && html`<div class="small" style="position: absolute; top: 10px; left: 10px; color: var(--err);">${error}</div>`}
      <button class="btn small" style="position: absolute; bottom: 10px; right: 10px;" onClick=${toggleRotate}>
        Rotate
      </button>
    </div>
  `;
}
