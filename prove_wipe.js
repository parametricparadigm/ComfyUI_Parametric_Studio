/* The wipe. A range input does the moving, so it works with a finger, a mouse and the arrow keys, and needs no animation. */
import { useState } from "preact/hooks";
import { html } from "./common.js";

export function Wipe({ base, frame }) {
  const [pos, setPos] = useState(50), [heat, setHeat] = useState(false);
  const at = frame.at == null ? "" : ` at ${Math.round(frame.at * 100)} percent of the clip`;
  return html`<figure class="pv-wipe"><div class="pv-stage">
      <img src=${`${base}/ours_${frame.i}.png`} alt=${"Ours" + at}/>
      <img class="pv-top" src=${`${base}/yours_${frame.i}.png`} alt=${"Yours" + at} style=${{ clipPath: `inset(0 ${100 - pos}% 0 0)` }}/>
      ${heat && html`<img class="pv-heat" src=${`${base}/diff_${frame.i}.png`} alt=${"Where the two differ" + at}/>`}
      <i class="pv-bar" style=${{ left: pos + "%" }} aria-hidden="true"></i>
      <span class="pv-side l">Yours</span><span class="pv-side r">Ours</span></div>
    <label class="fx-lab">Wipe between yours and ours<input type="range" min="0" max="100" value=${pos} onInput=${(e) => setPos(+e.target.value)}/></label>
    <figcaption class="fx-row small"><span>Mean difference <b>${frame.mean_diff}</b> of 255. <b>${frame.pct_off}%</b> of pixels off by more than ${frame.off_by}.${frame.resized ? " Yours was scaled to ours to compare them." : ""} <span class="fx-tag measured">measured</span></span><button class="btn small" type="button" aria-pressed=${heat} onClick=${() => setHeat(!heat)}>${heat ? "Hide the differences" : "Show the differences"}</button></figcaption></figure>`;
}
