import { html } from "./common.js";
import { pathFor, trend } from "./sparkline_math.js";

export function Sparkline({ values, w = 120, h = 32, label }) {
  const { d, last } = pathFor(values, w, h);
  const t = trend(values);
  const lastVal = values && values.length > 0 ? values[values.length - 1] : 0;
  const ariaLabel = `${label}: ${lastVal}, ${t}`;

  return html`
    <svg
      width="${w}"
      height="${h}"
      viewBox="0 0 ${w} ${h}"
      role="img"
      aria-label="${ariaLabel}"
    >
      <defs>
        <linearGradient id="spark-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="var(--a2)" stop-opacity="0.3" />
          <stop offset="100%" stop-color="var(--a2)" stop-opacity="0" />
        </linearGradient>
      </defs>
      ${d ? html`
        <path
          d="${d} L ${last.x} ${h} L ${last.x} ${h}"
          fill="url(#spark-grad)"
          stroke="none"
        />
        <path
          d="${d}"
          fill="none"
          stroke="var(--a2)"
          stroke-width="1.5"
        />
        <circle
          cx="${last.x}"
          cy="${last.y}"
          r="2"
          fill="var(--a2)"
        />
      ` : null}
    </svg>
  `;
}
