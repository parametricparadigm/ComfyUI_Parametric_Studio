import { useEffect } from "preact/hooks";
import { html } from "./common.js";

export function useShortcuts(registry) {
  useEffect(() => {
    function onKeyDown(event) {
      registry.handle(event);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [registry]);
}

export function ShortcutHelp({ registry, onClose }) {
  const items = registry.list();
  return html`
    <div role="dialog" aria-modal="true" class="card" style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;z-index:1000;">
      <div class="card" style="max-width:400px;width:90%;padding:1rem;">
        <div class="row" style="justify-content:space-between;margin-bottom:1rem;">
          <h3>Keyboard Shortcuts</h3>
          <button class="btn small" onclick=${onClose}>Close</button>
        </div>
        <ul style="list-style:none;padding:0;margin:0;">
          ${items.map(item => html`
            <li class="row" style="padding:0.5rem 0;border-bottom:1px solid var(--line);">
              <span>${item.label}</span>
              <span class="chip">${item.combo}</span>
            </li>
          `)}
        </ul>
      </div>
    </div>
  `;
}
