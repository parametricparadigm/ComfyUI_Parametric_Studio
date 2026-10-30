/* Share a result: the phone's share sheet when it can send files, otherwise a caption to copy plus post links. Nothing is posted by the studio; the person presses the button on the other side. */
import { useState } from "preact/hooks";
import { html } from "./common.js";

const caption = (prompt, family) => `"${(prompt || "").slice(0, 140)}"\nMade on my own GPU with ${family ? family + " and " : ""}Parametric Studio, open source on ComfyUI. Every frame has its graph. #OpenSourceHiggsfield`;

export function ShareButton({ url, prompt, family, cls }) {
  const [open, setOpen] = useState(false); const [copied, setCopied] = useState(false); const text = caption(prompt, family);
  const go = async () => {
    try {
      if (navigator.canShare) { const r = await fetch(url); const b = await r.blob(); const f = new File([b], url.split("/").pop().split("?")[0] || "parametric-studio", { type: b.type }); if (navigator.canShare({ files: [f] })) { await navigator.share({ files: [f], text }); return; } }
    } catch (e) { if (e && e.name === "AbortError") return; }
    setOpen(true);
  };
  const copy = async () => { try { await navigator.clipboard.writeText(text); setCopied(true); } catch {} };
  const q = encodeURIComponent(text);
  return html`<span style="display:contents"><button class=${cls || "btn small primary"} onClick=${(e) => { e.stopPropagation(); go(); }}>Share</button>
    ${open && html`<div class="modal" onClick=${(e) => { e.stopPropagation(); setOpen(false); }}><div class="box phonebox" onClick=${(e) => e.stopPropagation()}><h2>Share it</h2><p class="small" style="white-space:pre-wrap">${text}</p>
      <div class="row"><button class="btn small primary" onClick=${copy}>${copied ? "Copied" : "Copy caption"}</button><a class="btn small" href=${url} download>Download the file</a><a class="btn small" href=${"https://x.com/intent/post?text=" + q} target="_blank" rel="noopener">X</a><a class="btn small" href=${"https://www.reddit.com/submit?title=" + encodeURIComponent("Made locally with Parametric Studio on ComfyUI") + "&text=" + q} target="_blank" rel="noopener">Reddit</a><button class="btn small" onClick=${() => setOpen(false)}>Close</button></div>
      <p class="small">Attach the downloaded file to your post.</p></div></div>`}</span>`;
}
