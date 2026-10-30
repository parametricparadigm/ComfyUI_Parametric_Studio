export function fitDistance(box, fovDeg, aspect) {
  const min = box.min;
  const max = box.max;
  const dx = max[0] - min[0];
  const dy = max[1] - min[1];
  const dz = max[2] - min[2];

  if (dx === 0 && dy === 0 && dz === 0) {
    return 1;
  }

  const cx = (min[0] + max[0]) / 2;
  const cy = (min[1] + max[1]) / 2;
  const cz = (min[2] + max[2]) / 2;

  const r = Math.sqrt(dx * dx + dy * dy + dz * dz) / 2;

  const vfov = (fovDeg * Math.PI) / 180;
  const hfov = 2 * Math.atan(Math.tan(vfov / 2) * aspect);
  const minFov = Math.min(vfov, hfov);

  return r / Math.sin(minFov / 2);
}
