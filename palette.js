import { h, render } from "preact";
import { useState, useEffect, useRef, useMemo } from "preact/hooks";
import html from "./common.js";
import { fuzzyScore, rank } from "./fuzzy.js";

// Re-export pure functions for testing
export { fuzzyScore, rank };

export function Palette({ items, onPick, onClose }) {
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef(null);

  const results = useMemo(() => rank(query, items, 8), [query, items]);

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  const handleKeyDown = (e) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex(i => (i + 1) % results.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex(i => (i - 1 + results.length) % results.length);
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (results[activeIndex]) {
        onPick(results[activeIndex]);
        onClose();
      }
    } else if (e.key === "Escape") {
      e.preventDefault();
      onClose();
    }
  };

  const handlePick = (item) => {
    onPick(item);
    onClose();
  };

  return html`
    <div class="palette-overlay" role="dialog" aria-label="Command palette">
      <div class="palette-modal">
        <input
          ref=${inputRef}
          type="text"
          class="palette-input"
          placeholder="Type to search..."
          value=${query}
          oninput=${(e) => setQuery(e.target.value)}
          onkeydown=${handleKeyDown}
        />
        <ul class="palette-list">
          ${results.map((item, i) => html`
            <li
              class=${"palette-item" + (i === activeIndex ? " active" : "")}
              onclick=${() => handlePick(item)}
            >
              <span class="palette-label">${item.label}</span>
              ${item.hint ? html`<span class="palette-hint">${item.hint}</span>` : null}
            </li>
          `)}
        </ul>
      </div>
    </div>
  `;
}
