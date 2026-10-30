export function parseCombo(combo, isMac = false) {
  const parts = combo.toLowerCase().split('+').map(p => p.trim());
  const result = { key: '', ctrl: false, shift: false, alt: false, meta: false };
  for (const part of parts) {
    if (part === 'ctrl') result.ctrl = true;
    else if (part === 'shift') result.shift = true;
    else if (part === 'alt') result.alt = true;
    else if (part === 'meta') result.meta = true;
    else if (part === 'mod') {
      if (isMac) result.meta = true;
      else result.ctrl = true;
    } else {
      result.key = part;
    }
  }
  return result;
}

export function matches(combo, event) {
  const { key, ctrl, shift, alt, meta } = combo;
  if (key !== event.key.toLowerCase()) return false;
  if (ctrl !== event.ctrlKey) return false;
  if (shift !== event.shiftKey) return false;
  if (alt !== event.altKey) return false;
  if (meta !== event.metaKey) return false;
  return true;
}

export function isTyping(target) {
  if (!target) return false;
  const tag = (target.tagName || '').toLowerCase();
  if (tag === 'input' || tag === 'textarea' || tag === 'select') return true;
  if (target.isContentEditable) return true;
  return false;
}

export function createRegistry() {
  const entries = new Map();

  function add(combo, id, label, handler) {
    const parsed = parseCombo(combo);
    const key = JSON.stringify(parsed);
    if (entries.has(key)) {
      return { conflict: true, combo, existingId: entries.get(key).id };
    }
    entries.set(key, { combo, id, label, handler, parsed });
    return { conflict: false };
  }

  function list() {
    return Array.from(entries.values()).map(e => ({ combo: e.combo, id: e.id, label: e.label }));
  }

  function handle(event) {
    const target = event.target;
    const typing = isTyping(target);
    for (const entry of entries.values()) {
      if (matches(entry.parsed, event)) {
        if (typing && !entry.parsed.ctrl && !entry.parsed.meta) {
          continue;
        }
        entry.handler(event);
        return true;
      }
    }
    return false;
  }

  return { add, list, handle };
}
