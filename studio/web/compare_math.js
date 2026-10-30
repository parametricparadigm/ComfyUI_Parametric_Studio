export function clampPercent(x, left, width) {
  if (width <= 0) return 50;
  const p = ((x - left) / width) * 100;
  return Math.max(0, Math.min(100, p));
}
