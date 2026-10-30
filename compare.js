import { h } from "preact";
import { useState, useRef, useCallback } from "preact/hooks";
import { html } from "./common.js";
import { clampPercent } from "./compare_math.js";

export { clampPercent };

export function Compare({ before, after, labelBefore = 'Before', labelAfter = 'After', height }) {
  const [pos, setPos] = useState(50);
  const containerRef = useRef(null);
  const handleRef = useRef(null);

  const updateFromPointer = useCallback((clientX) => {
    const el = containerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const p = clampPercent(clientX, rect.left, rect.width);
    setPos(p);
  }, []);

  const onPointerDown = (e) => {
    e.preventDefault();
    const handle = handleRef.current;
    if (handle) {
      handle.setPointerCapture(e.pointerId);
    }
    updateFromPointer(e.clientX);
  };

  const onPointerMove = (e) => {
    if (e.buttons !== 1) return;
    updateFromPointer(e.clientX);
  };

  const onPointerUp = (e) => {
    const handle = handleRef.current;
    if (handle && handle.hasPointerCapture(e.pointerId)) {
      handle.releasePointerCapture(e.pointerId);
    }
  };

  const onKeyDown = (e) => {
    let next = pos;
    if (e.key === 'ArrowLeft') {
      next = Math.max(0, pos - 2);
    } else if (e.key === 'ArrowRight') {
      next = Math.min(100, pos + 2);
    } else if (e.key === 'Home') {
      next = 0;
    } else if (e.key === 'End') {
      next = 100;
    } else {
      return;
    }
    e.preventDefault();
    setPos(next);
  };

  const style = {
    position: 'relative',
    width: '100%',
    height: height || '300px',
    overflow: 'hidden',
    userSelect: 'none',
    touchAction: 'none'
  };

  const beforeStyle = {
    position: 'absolute',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    objectFit: 'contain',
    zIndex: 1
  };

  const afterStyle = {
    position: 'absolute',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    objectFit: 'contain',
    zIndex: 2,
    clipPath: `inset(0 ${100 - pos}% 0 0)`
  };

  const dividerStyle = {
    position: 'absolute',
    top: 0,
    bottom: 0,
    left: `${pos}%`,
    width: '4px',
    marginLeft: '-2px',
    background: 'var(--a1)',
    zIndex: 3,
    cursor: 'ew-resize'
  };

  const handleStyle = {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    width: '44px',
    height: '44px',
    borderRadius: '50%',
    background: 'var(--a1)',
    border: '2px solid var(--bg)',
    cursor: 'ew-resize',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 4
  };

  const labelStyle = {
    position: 'absolute',
    top: '10px',
    padding: '4px 8px',
    background: 'rgba(0,0,0,0.5)',
    color: 'white',
    fontSize: '12px',
    zIndex: 5,
    pointerEvents: 'none'
  };

  return html`
    <div
      ref=${containerRef}
      style=${style}
      onPointerDown=${onPointerDown}
      onPointerMove=${onPointerMove}
      onPointerUp=${onPointerUp}
    >
      <img src=${before} style=${beforeStyle} alt=${labelBefore} />
      <img src=${after} style=${afterStyle} alt=${labelAfter} />
      <div style=${dividerStyle}>
        <div
          ref=${handleRef}
          style=${handleStyle}
          role="slider"
          aria-valuenow=${pos}
          aria-valuemin=${0}
          aria-valuemax=${100}
          aria-label="Compare slider"
          tabIndex=${0}
          onKeyDown=${onKeyDown}
        >
          <span style=${{ color: 'var(--bg)', fontSize: '16px' }}>↔</span>
        </div>
      </div>
      <div style=${{ ...labelStyle, left: '10px' }}>${labelBefore}</div>
      <div style=${{ ...labelStyle, right: '10px' }}>${labelAfter}</div>
    </div>
  `;
}
