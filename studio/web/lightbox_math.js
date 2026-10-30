export function zoomAt(view, factor, cx, cy, min = 1, max = 8) {
  const newScale = Math.min(max, Math.max(min, view.scale * factor));
  const ratio = newScale / view.scale;
  const newX = cx - (cx - view.x) * ratio;
  const newY = cy - (cy - view.y) * ratio;
  return { scale: newScale, x: newX, y: newY };
}

export function clampPan(view, contentW, contentH, frameW, frameH) {
  const scaledW = contentW * view.scale;
  const scaledH = contentH * view.scale;
  let x = view.x;
  let y = view.y;

  if (scaledW <= frameW) {
    x = (frameW - scaledW) / 2;
  } else {
    x = Math.min(0, Math.max(frameW - scaledW, x));
  }

  if (scaledH <= frameH) {
    y = (frameH - scaledH) / 2;
  } else {
    y = Math.min(0, Math.max(frameH - scaledH, y));
  }

  return { scale: view.scale, x, y };
}

export function fitScale(contentW, contentH, frameW, frameH) {
  if (contentW === 0 || contentH === 0 || frameW === 0 || frameH === 0) return 1;
  return Math.min(frameW / contentW, frameH / contentH);
}

export function next(i, n, dir) {
  if (n <= 0) return 0;
  return ((i + dir) % n + n) % n;
}
