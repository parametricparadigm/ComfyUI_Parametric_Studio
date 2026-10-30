export function peaks(samples, buckets) {
  if (!samples || samples.length === 0 || buckets <= 0) {
    return new Array(buckets).fill(0);
  }

  const result = new Array(buckets).fill(0);
  const bucketSize = samples.length / buckets;

  for (let i = 0; i < buckets; i++) {
    const start = Math.floor(i * bucketSize);
    const end = Math.floor((i + 1) * bucketSize);
    let maxVal = 0;

    for (let j = start; j < end; j++) {
      const val = Math.abs(samples[j]);
      if (val > maxVal) {
        maxVal = val;
      }
    }
    result[i] = maxVal;
  }

  let globalMax = 0;
  for (let i = 0; i < buckets; i++) {
    if (result[i] > globalMax) {
      globalMax = result[i];
    }
  }

  if (globalMax > 0) {
    for (let i = 0; i < buckets; i++) {
      result[i] = result[i] / globalMax;
    }
  }

  return result;
}

export function timeToX(t, duration, width) {
  if (duration <= 0) return 0;
  return (t / duration) * width;
}

export function xToTime(x, duration, width) {
  if (width <= 0) return 0;
  const t = (x / width) * duration;
  return Math.max(0, Math.min(duration, t));
}
