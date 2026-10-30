export function pathFor(values, w, h, pad = 2, min = null, max = null) {
  if (!values || values.length === 0) {
    return { d: '', last: { x: 0, y: 0 } };
  }

  const n = values.length;
  let vMin = min !== null ? min : Math.min(...values);
  let vMax = max !== null ? max : Math.max(...values);

  if (vMin === vMax) {
    const y = h / 2;
    const x0 = pad;
    const x1 = w - pad;
    return {
      d: `M ${x0} ${y} L ${x1} ${y}`,
      last: { x: x1, y }
    };
  }

  const range = vMax - vMin;
  const stepX = (w - 2 * pad) / (n - 1);
  const points = [];

  for (let i = 0; i < n; i++) {
    const x = pad + i * stepX;
    const norm = (values[i] - vMin) / range;
    const y = h - pad - norm * (h - 2 * pad);
    points.push({ x, y });
  }

  let d = `M ${points[0].x} ${points[0].y}`;
  for (let i = 1; i < n; i++) {
    d += ` L ${points[i].x} ${points[i].y}`;
  }

  return {
    d,
    last: points[n - 1]
  };
}

export function ringPush(arr, v, cap = 60) {
  const next = [...arr, v];
  if (next.length > cap) {
    next.shift();
  }
  return next;
}

export function trend(values) {
  if (!values || values.length < 3) {
    return 'flat';
  }

  const n = values.length;
  const third = Math.floor(n / 3);
  const firstThird = values.slice(0, third);
  const lastThird = values.slice(n - third);

  const meanFirst = firstThird.reduce((a, b) => a + b, 0) / firstThird.length;
  const meanLast = lastThird.reduce((a, b) => a + b, 0) / lastThird.length;

  const diff = meanLast - meanFirst;
  const tolerance = 0.03 * Math.max(Math.abs(meanFirst), Math.abs(meanLast), 1);

  if (diff > tolerance) return 'up';
  if (diff < -tolerance) return 'down';
  return 'flat';
}
