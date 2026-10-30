export function createToasts() {
  return { items: [], nextId: 1 };
}

export function pushToast(state, { kind = 'info', text, ms = 4000, now = Date.now() }) {
  const items = [...state.items];
  let nextId = state.nextId;

  // Check for duplicate text within the last 1000 ms
  const dupIndex = items.findIndex(
    (item) => item.text === text && (now - item.createdAt) < 1000
  );

  if (dupIndex !== -1) {
    const updated = { ...items[dupIndex], count: items[dupIndex].count + 1 };
    items[dupIndex] = updated;
    return { items, nextId };
  }

  const id = nextId++;
  const item = {
    id,
    kind,
    text,
    count: 1,
    createdAt: now,
    until: now + ms
  };

  items.push(item);

  // Max 4 visible: drop oldest if exceeded
  if (items.length > 4) {
    items.shift();
  }

  return { items, nextId };
}

export function dismiss(state, id) {
  const items = state.items.filter((item) => item.id !== id);
  return { items, nextId: state.nextId };
}

export function expire(state, now) {
  const items = state.items.filter((item) => item.until > now);
  return { items, nextId: state.nextId };
}
