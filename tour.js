import { h, render } from "preact";
import { useState, useEffect, useRef, useMemo } from "preact/hooks";
import html from "./common.js";
import { createTour, start, next, back, skip, current, progress } from "./tour_logic.js";

export function Tour({ steps, onClose, speak }) {
  const [tour, setTour] = useState(() => start(createTour(steps)));

  const [rect, setRect] = useState(null);
  const overlayRef = useRef(null);

  const step = current(tour);
  const prog = progress(tour);

  useEffect(() => {
    if (!step) return;
    
    if (step.tab) {
      window.location.hash = step.tab;
    }

    if (typeof speak === 'function') {
      speak(step.text);
    }

    const updateRect = () => {
      if (step.target) {
        const el = document.querySelector(step.target);
        if (el) {
          const r = el.getBoundingClientRect();
          setRect({ top: r.top, left: r.left, width: r.width, height: r.height });
        } else {
          setRect(null);
        }
      } else {
        setRect(null);
      }
    };

    updateRect();
    const settle = setTimeout(() => {
      const el = step.target && document.querySelector(step.target);
      if (el) el.scrollIntoView({ block: 'center', inline: 'nearest' });
      updateRect();
    }, 150);
    window.addEventListener('resize', updateRect);
    window.addEventListener('scroll', updateRect, true);

    return () => {
      clearTimeout(settle);
      window.removeEventListener('resize', updateRect);
      window.removeEventListener('scroll', updateRect, true);
    };
  }, [step, speak]);

  useEffect(() => {
    const handleKey = (e) => {
      const el = e.target || {};
      if (/^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName || '') || el.isContentEditable) return;
      if (e.key === 'ArrowRight') {
        handleNext();
      } else if (e.key === 'ArrowLeft') {
        handleBack();
      } else if (e.key === 'Escape') {
        handleSkip();
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [tour]);

  const finish = () => {
    if (onClose) onClose();
  };

  const handleNext = () => {
    const newTour = next(tour);
    setTour(newTour);
    if (newTour.done) {
      finish();
    }
  };

  const handleBack = () => {
    setTour(back(tour));
  };

  const handleSkip = () => {
    const newTour = skip(tour);
    setTour(newTour);
    finish();
  };

  if (tour.done) return null;

  const spotlightStyle = rect
    ? {
        top: `${rect.top - 8}px`,
        left: `${rect.left - 8}px`,
        width: `${rect.width + 16}px`,
        height: `${rect.height + 16}px`
      }
    : null;

  return html`
    <div class=${"tour-overlay" + (spotlightStyle ? "" : " dim")} role="dialog" aria-label="Guided Tour">
      ${spotlightStyle ? html`
        <div class="tour-spotlight" style=${spotlightStyle}></div>
      ` : null}
      <div class="tour-card">
        <div class="tour-header">
          <span class="tour-name">Comfy Prime</span>
          <span class="tour-step">${prog.index + 1} / ${prog.total}</span>
        </div>
        <h3 class="tour-title">${step.title}</h3>
        <p class="tour-text">${step.text}</p>
        <div class="tour-dots">
          ${steps.map((s, i) => html`
            <span class="tour-dot ${i === prog.index ? 'on' : ''}"></span>
          `)}
        </div>
        <div class="tour-actions">
          <button class="btn small" onClick=${handleBack} disabled=${prog.index === 0}>Back</button>
          <button class="btn small" onClick=${handleSkip}>Skip</button>
          <button class="btn small" onClick=${handleNext}>Next</button>
        </div>
      </div>
    </div>
  `;
}
