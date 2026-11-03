import { h } from "preact";
import { useState, useEffect, useRef } from "preact/hooks";
import html from "./common.js";
import { peaks, timeToX, xToTime } from "./waveform_math.js";

export function Waveform({ url, height = 64, onSeek }) {
  const canvasRef = useRef(null);
  const audioRef = useRef(null);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState(null);
  const [peaksData, setPeaksData] = useState(null);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [width, setWidth] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let audioContext = null;
    let observer = null;

    const loadWaveform = async () => {
      try {
        setStatus("loading");
        setError(null);

        const response = await fetch(url);
        if (!response.ok) throw new Error("Failed to fetch audio");
        const arrayBuffer = await response.arrayBuffer();

        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        audioContext = new AudioCtx();
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

        if (cancelled) return;

        setDuration(audioBuffer.duration);
        
        const canvas = canvasRef.current;
        if (canvas) {
          const w = canvas.clientWidth;
          const h = canvas.clientHeight;
          canvas.width = w;
          canvas.height = h;
          setWidth(w);

          const channelData = audioBuffer.getChannelData(0);
          const p = peaks(channelData, w);
          setPeaksData(p);
          setStatus("ready");
        }
      } catch (e) {
        if (!cancelled) {
          setError(e.message);
          setStatus("error");
        }
      }
    };

    loadWaveform();

    const canvas = canvasRef.current;
    if (canvas) {
      observer = new ResizeObserver(() => {
        const w = canvas.clientWidth;
        const h = canvas.clientHeight;
        canvas.width = w;
        canvas.height = h;
        setWidth(w);
        
        if (peaksData) {
          drawWaveform(canvas, peaksData, currentTime, duration, w, h);
        }
      });
      observer.observe(canvas);
    }

    return () => {
      cancelled = true;
      if (observer) observer.disconnect();
      if (audioContext) audioContext.close();
    };
  }, [url]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || status !== "ready") return;

    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime);
      const canvas = canvasRef.current;
      if (canvas && peaksData) {
        drawWaveform(canvas, peaksData, audio.currentTime, duration, canvas.width, canvas.height);
      }
    };

    audio.addEventListener("timeupdate", handleTimeUpdate);
    return () => audio.removeEventListener("timeupdate", handleTimeUpdate);
  }, [status, peaksData, duration]);

  const handleClick = (e) => {
    if (status !== "ready" || !duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const t = xToTime(x, duration, rect.width);
    
    if (onSeek) onSeek(t);
    
    const audio = audioRef.current;
    if (audio) {
      audio.currentTime = t;
      setCurrentTime(t);
    }
  };

  const drawWaveform = (canvas, p, time, dur, w, h) => {
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, w, h);

    const playedX = timeToX(time, dur, w);
    
    const style = getComputedStyle(document.documentElement);
    const colorPlayed = style.getPropertyValue("--a1").trim() || "#00ff00";
    const colorRest = style.getPropertyValue("--line").trim() || "#333333";

    const midY = h / 2;
    const barWidth = 1;
    const gap = 1;
    const totalBarWidth = barWidth + gap;

    for (let i = 0; i < p.length; i++) {
      const x = i * totalBarWidth;
      if (x >= w) break;

      const amp = p[i] * (h / 2);
      const color = x <= playedX ? colorPlayed : colorRest;

      ctx.fillStyle = color;
      ctx.fillRect(x, midY - amp, barWidth, amp * 2);
    }
  };

  return html`
    <div class="waveform-container" style="position: relative; width: 100%; height: ${height}px;">
      <canvas 
        ref=${canvasRef} 
        style="width: 100%; height: 100%; display: block; cursor: pointer;"
        onClick=${handleClick}
      />
      ${status === "loading" && html`<div class="pp-wavewait" role="status"><span class="fx-sr">Loading the waveform.</span></div>`}
      ${status === "error" && html`<div class="small" style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; align-items: center; justify-content: center; background: var(--panel); color: var(--err);">${error}</div>`}
      <audio ref=${audioRef} src=${url} style="display: none;" />
    </div>
  `;
}
