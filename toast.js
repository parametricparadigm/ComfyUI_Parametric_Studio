import { h } from "preact";
import { html } from "./common.js";

export function Toasts({ state, onDismiss }) {
  const style = html`
    <style>
      @keyframes toast-in {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
      }
      .toast-item {
        animation: toast-in 0.2s ease-out;
      }
      @media (prefers-reduced-motion: reduce) {
        .toast-item {
          animation: none;
        }
      }
    </style>
  `;

  return html`
    ${style}
    <div
      role="status"
      aria-live="polite"
      style="position: fixed; bottom: 1rem; right: 1rem; display: flex; flex-direction: column; gap: 0.5rem; z-index: 9999;"
    >
      ${state.items.map((item) => {
        const borderColor =
          item.kind === 'ok' ? 'var(--ok)' :
          item.kind === 'warn' ? 'var(--warn)' :
          item.kind === 'error' ? 'var(--err)' :
          'var(--a2)';

        return html`
          <div
            class="toast-item card"
            style="border-left: 4px solid ${borderColor}; padding: 0.75rem 1rem; min-width: 250px; max-width: 350px; display: flex; align-items: center; justify-content: space-between; gap: 0.5rem;"
          >
            <span class="small">${item.text}${item.count > 1 ? ` (${item.count})` : ''}</span>
            <button
              class="btn small"
              onClick=${() => onDismiss(item.id)}
              aria-label="Dismiss notification"
            >
              ×
            </button>
          </div>
        `;
      })}
    </div>
  `;
}
