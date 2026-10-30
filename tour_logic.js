export function createTour(steps) {
  return {
    steps,
    index: 0,
    done: false
  };
}

export function start(t) {
  if (t.done) return t;
  return { ...t, index: 0, done: false };
}

export function next(t) {
  if (t.done) return t;
  if (t.index >= t.steps.length - 1) {
    return { ...t, done: true };
  }
  return { ...t, index: t.index + 1 };
}

export function back(t) {
  if (t.done || t.index === 0) return t;
  return { ...t, index: t.index - 1 };
}

export function skip(t) {
  return { ...t, done: true };
}

export function current(t) {
  if (t.done) return null;
  return t.steps[t.index] || null;
}

export function progress(t) {
  return {
    index: t.index,
    total: t.steps.length,
    done: t.done
  };
}

export function shouldAutoStart(storageValue) {
  return storageValue !== 'done';
}
