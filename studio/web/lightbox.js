import { h, render } from "preact";
import { useState, useEffect, useRef } from "preact/hooks";
import html from "./common.js";
import { zoomAt, clampPan, fitScale, next } from "./lightbox_math.js";

export function Lightbox({ items, index, onClose, onIndex }) {
  const [view, setView] = useState({ scale: 1, x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0, vx: 0, vy: 0 });
  const dialogRef = useRef(null);
  const item = items[index];

  useEffect(() => {
    if (!item) return;
    const w = window.innerWidth;
    const h = window.innerHeight;
    const scale = fitScale(1000, 1000, w, h);
    const x = (w - 1000 * scale) / 2;
    const y = (h - 1000 * scale) / 2;
    setView({ scale, x, y });
    if (dialogRef.current) dialogRef.current.focus();
  }, [index]);

  useEffect(() => {
    const handleKey = (e) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'ArrowRight') onIndex(next(index, items.length, 1));
      if (e.key === 'ArrowLeft') onIndex(next(index, items.length, -1));
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [index, items.length, onClose, onIndex]);

  const onWheel = (e) => {
    e.preventDefault();
    const rect = dialogRef.current.getBoundingClientRect();
    const cx = e.clientX - rect.left;
    const cy = e.clientY - rect.top;
    const factor = e.deltaY < 0 ? 1.1 : 0.9;
    const newView = zoomAt(view, factor, cx, cy);
    setView(clampPan(newView, 1000, 1000, rect.width, rect.height));
  };

  const onDoubleClick = (e) => {
    const rect = dialogRef.current.getBoundingClientRect();
    const cx = e.clientX - rect.left;
    const cy = e.clientY - rect.top;
    const factor = view.scale > 1 ? 1 / view.scale : 2;
    const newView = zoomAt(view, factor, cx, cy);
    setView(clampPan(newView, 1000, 1000, rect.width, rect.height));
  };

  const onMouseDown = (e) => {
    setDragging(true);
    dragStart.current = { x: e.clientX, y: e.clientY, vx: view.x, vy: view.y };
  };

  const onMouseMove = (e) => {
    if (!dragging) return;
    const dx = e.clientX - dragStart.current.x;
    const dy = e.clientY - dragStart.current.y;
    const rect = dialogRef.current.getBoundingClientRect();
    const newView = {
      scale: view.scale,
      x: dragStart.current.vx + dx,
      y: dragStart.current.vy + dy
    };
    setView(clampPan(newView, 1000, 1000, rect.width, rect.height));
  };

  const onMouseUp = () => setDragging(false);

  return html`
    <div class="lightbox-overlay" role="dialog" aria-modal="true" ref=${dialogRef} tabindex="-1"
         onWheel=${onWheel} onDoubleClick=${onDoubleClick}
         onMouseDown=${onMouseDown} onMouseMove=${onMouseMove} onMouseUp=${onMouseUp} onMouseLeave=${onMouseUp}>
      <div class="lightbox-content" style="transform: translate(${view.x}px, ${view.y}px) scale(${view.scale});">
        ${item.kind === 'image' ? html`<img src=${item.url} alt=${item.title} />` : ''}
        ${item.kind === 'video' ? html`<video src=${item.url} controls />` : ''}
        ${item.kind === 'audio' ? html`<audio src=${item.url} controls />` : ''}
      </div>
      <button class="btn small" onClick=${() => onIndex(next(index, items.length, -1))}>Prev</button>
      <button class="btn small" onClick=${() => onIndex(next(index, items.length, 1))}>Next</button>
      <button class="btn small" onClick=${onClose}>Close</button>
    </div>
  `;
}
