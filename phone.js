/* "Use on your phone": a QR code for this studio's private address. The studio itself runs on the computer; the phone is a screen for it. */
import { useEffect, useRef, useState } from "preact/hooks";
import { html, api } from "./common.js";

function Qr({ text }) {
  const ref = useRef(null);
  useEffect(() => { let dead = false; const draw = () => { if (dead || !ref.current || !window.qrcode) return; const q = window.qrcode(0, "M"); q.addData(text); q.make(); ref.current.innerHTML = q.createSvgTag({ cellSize: 5, margin: 2, scalable: true }); };
    if (window.qrcode) draw(); else { const s = document.createElement("script"); s.src = "vendor/qrcode.js"; s.onload = draw; document.head.appendChild(s); } return () => { dead = true; }; }, [text]);
  return html`<div class="qr" ref=${ref} role="img" aria-label=${"QR code for " + text}></div>`;
}

export function PhonePanel({ onClose }) {
  const [p, setP] = useState(null); const [err, setErr] = useState("");
  useEffect(() => { api("/api/phone").then(setP).catch((e) => setErr(e.message)); }, []);
  const url = p && (p.url || p.lan_url); const ts = p && p.tailscale;
  return html`<div class="modal" onClick=${onClose}><div class="box phonebox" onClick=${(e) => e.stopPropagation()}>
    <h2>Use on your phone</h2>
    ${err && html`<p class="small" style="color:var(--err)">${err}</p>`}
    ${url ? html`<${Qr} text=${url}/><p class="small">Scan it with your phone's camera. Then choose <b>Add to Home Screen</b> in the browser menu to install it as an app.</p><p class="small"><code>${p.url || "your local network address"}</code></p>${!p.url && html`<p class="small">This is a plain local-network link: the mic and installing as an app need the Tailscale route below.</p>`}` : null}
    ${p && !p.url && html`<ol class="small phonesteps">
      ${!ts.installed && html`<li>Install Tailscale on this computer and your phone, and sign in to the same account. It is free for personal use.</li>`}
      ${ts.installed && !ts.connected && html`<li>Connect Tailscale on this computer: <code>tailscale up</code></li>`}
      <li>Run this on the computer, once: <code>${p.serve_command}</code>${ts.connected ? " (it asks you to enable HTTPS for your tailnet the first time)." : ""}</li>
      <li>Reopen this panel and scan the code.</li></ol>
      <p class="small">No Tailscale? On the computer start the studio with <code>${p.lan_command}</code>. It prints a private pairing link, and this panel will show its code.</p>`}
    <p class="small">Your renders still run on this computer's GPU, and it has to be on. Only devices on your own Tailscale account can reach the Tailscale address.</p>
    <div class="row"><button class="btn small" onClick=${onClose}>Close</button></div></div></div>`;
}
