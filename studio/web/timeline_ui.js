import { h, render } from "preact";
import { useState, useEffect, useRef, useMemo } from "preact/hooks";
import htm from "htm";
import { createTimeline, addClip, moveClip, trimClip, splitAt, removeClip, setPlayhead, duration, toEDL, validateEDL, addTrack } from './timeline_core.js';

const html = htm.bind(h);

export function Timeline({ library, onRender, rendering }) {
  const [state, setState] = useState(() => createTimeline());
  const [selectedLib, setSelectedLib] = useState(null);
  const [selectedClip, setSelectedClip] = useState(null);
  const [pxPerSecond, setPxPerSecond] = useState(80);
  const [problems, setProblems] = useState([]);
  const [drag, setDrag] = useState(null);
  const containerRef = useRef(null);

  const totalDur = useMemo(() => duration(state), [state]);
  const width = Math.max(600, totalDur * pxPerSecond + 100);

  const snap = (sec) => Math.round(sec * 10) / 10;

  const getPos = (e) => {
    const rect = containerRef.current.getBoundingClientRect();
    return snap(Math.max(0, (e.clientX - rect.left) / pxPerSecond));
  };

  const handleAdd = () => {
    if (!selectedLib) return;
    const item = library.find(l => l.src === selectedLib);
    if (!item || item.kind === 'image') return;
    const trackIdx = state.tracks.findIndex(t => t.kind === item.kind);
    let newState = state;
    if (trackIdx === -1) {
      newState = addTrack(newState, item.kind);
    }
    const finalTrackIdx = newState.tracks.findIndex(t => t.kind === item.kind);
    const clip = { src: item.src, label: item.label, kind: item.kind, dur: item.dur };
    newState = addClip(newState, finalTrackIdx, clip, 0);
    setState(newState);
  };

  const handleSplit = () => {
    if (!selectedClip) return;
    const newState = splitAt(state, selectedClip.track, selectedClip.id, state.playhead);
    if (newState !== state) setState(newState);
  };

  const handleDelete = () => {
    if (!selectedClip) return;
    const newState = removeClip(state, selectedClip.track, selectedClip.id);
    if (newState !== state) {
      setState(newState);
      setSelectedClip(null);
    }
  };

  const handleRippleDelete = () => {
    if (!selectedClip) return;
    // Simple ripple: remove and shift subsequent clips in that track
    const track = state.tracks[selectedClip.track];
    const idx = track.clips.findIndex(c => c.id === selectedClip.id);
    if (idx === -1) return;
    const clip = track.clips[idx];
    let newState = removeClip(state, selectedClip.track, selectedClip.id);
    // Shift clips after idx
    const newTrack = newState.tracks[selectedClip.track];
    for (let i = idx; i < newTrack.clips.length; i++) {
      const c = newTrack.clips[i];
      newState = moveClip(newState, selectedClip.track, c.id, c.start - clip.dur);
    }
    setState(newState);
    setSelectedClip(null);
  };

  const handleRender = () => {
    const edl = toEDL(state);
    const validation = validateEDL(edl);
    if (validation.ok) {
      onRender(edl);
    } else {
      setProblems(validation.problems || [validation.error || "Validation failed"]);
    }
  };

  const handleRulerClick = (e) => {
    const t = getPos(e);
    setState(setPlayhead(state, t));
  };

  const handleClipClick = (e, trackIdx, clipId) => {
    e.stopPropagation();
    setSelectedClip({ track: trackIdx, id: clipId });
  };

  const handleClipPointerDown = (e, trackIdx, clipId, clip) => {
    e.stopPropagation();
    setSelectedClip({ track: trackIdx, id: clipId });
    const startX = e.clientX;
    const startSec = clip.start;
    setDrag({ type: 'move', trackIdx, clipId, startX, startSec });
  };

  const handleEdgePointerDown = (e, trackIdx, clipId, side) => {
    e.stopPropagation();
    setSelectedClip({ track: trackIdx, id: clipId });
    const startX = e.clientX;
    const clip = state.tracks[trackIdx].clips.find(c => c.id === clipId);
    const startSec = side === 'left' ? clip.start : clip.start + clip.dur;
    setDrag({ type: 'trim', trackIdx, clipId, side, startX, startSec });
  };

  useEffect(() => {
    if (!drag) return;

    const onMove = (e) => {
      const dx = e.clientX - drag.startX;
      const dSec = dx / pxPerSecond;
      let newState = state;

      if (drag.type === 'move') {
        const newStart = snap(drag.startSec + dSec);
        if (newStart >= 0) {
          newState = moveClip(state, drag.trackIdx, drag.clipId, newStart);
        }
      } else if (drag.type === 'trim') {
        const clip = state.tracks[drag.trackIdx].clips.find(c => c.id === drag.clipId);
        if (!clip) return;
        if (drag.side === 'left') {
          const newStart = snap(drag.startSec + dSec);
          const maxStart = clip.start + clip.dur - 0.1;
          if (newStart >= 0 && newStart <= maxStart) {
            newState = trimClip(state, drag.trackIdx, drag.clipId, newStart, clip.start + clip.dur);
          }
        } else {
          const newEnd = snap(drag.startSec + dSec);
          const minEnd = clip.start + 0.1;
          if (newEnd >= minEnd) {
            newState = trimClip(state, drag.trackIdx, drag.clipId, clip.start, newEnd);
          }
        }
      }
      setState(newState);
    };

    const onUp = () => setDrag(null);

    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    return () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
    };
  }, [drag, state, pxPerSecond]);

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (selectedClip) handleDelete();
      } else if (e.key === 's') {
        handleSplit();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [selectedClip, state]);

  const styles = {
    container: {
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--bg)',
      color: 'var(--text)',
      fontFamily: 'system-ui, sans-serif',
      fontSize: '14px',
      border: '1px solid var(--line)',
      borderRadius: '8px',
      overflow: 'hidden'
    },
    toolbar: {
      display: 'flex',
      gap: '8px',
      padding: '8px',
      background: 'var(--panel)',
      borderBottom: '1px solid var(--line)',
      alignItems: 'center'
    },
    libraryStrip: {
      display: 'flex',
      gap: '8px',
      padding: '8px',
      background: 'var(--panel2)',
      borderBottom: '1px solid var(--line)',
      overflowX: 'auto'
    },
    libItem: (selected) => ({
      padding: '4px 8px',
      borderRadius: '4px',
      cursor: 'pointer',
      background: selected ? 'var(--a1)' : 'var(--panel)',
      color: selected ? 'var(--bg)' : 'var(--text)',
      border: '1px solid var(--line)',
      whiteSpace: 'nowrap'
    }),
    timelineArea: {
      position: 'relative',
      overflowX: 'auto',
      overflowY: 'hidden',
      background: 'var(--bg)'
    },
    ruler: {
      position: 'relative',
      height: '24px',
      background: 'var(--panel)',
      borderBottom: '1px solid var(--line)',
      cursor: 'crosshair',
      userSelect: 'none'
    },
    tick: (sec) => ({
      position: 'absolute',
      left: `${sec * pxPerSecond}px`,
      top: '0',
      bottom: '0',
      width: '1px',
      background: 'var(--line)',
      pointerEvents: 'none'
    }),
    tickLabel: (sec) => ({
      position: 'absolute',
      left: `${sec * pxPerSecond + 4}px`,
      top: '4px',
      fontSize: '10px',
      color: 'var(--mut)',
      pointerEvents: 'none'
    }),
    track: {
      position: 'relative',
      height: '40px',
      borderBottom: '1px solid var(--line)',
      background: 'var(--bg)'
    },
    clip: (selected) => ({
      position: 'absolute',
      top: '4px',
      height: '32px',
      borderRadius: '4px',
      background: selected ? 'var(--a2)' : 'var(--a1)',
      color: 'var(--bg)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: '12px',
      overflow: 'hidden',
      whiteSpace: 'nowrap',
      cursor: 'grab',
      userSelect: 'none',
      border: '1px solid var(--line)'
    }),
    edge: (side) => ({
      position: 'absolute',
      top: '0',
      bottom: '0',
      width: '8px',
      cursor: 'ew-resize',
      background: 'transparent',
      zIndex: 2
    }),
    playhead: {
      position: 'absolute',
      top: '0',
      bottom: '0',
      width: '2px',
      background: 'var(--err)',
      pointerEvents: 'none',
      zIndex: 10
    },
    problems: {
      padding: '8px',
      background: 'var(--panel)',
      borderTop: '1px solid var(--line)',
      color: 'var(--err)',
      fontSize: '12px'
    }
  };

  const ticks = [];
  for (let s = 0; s <= Math.ceil(totalDur); s++) {
    ticks.push(s);
  }

  return html`
    <div style=${styles.container}>
      <div style=${styles.toolbar}>
        <button class="btn small" onClick=${handleAdd}>Add selected</button>
        <button class="btn small" onClick=${handleSplit}>Split at playhead</button>
        <button class="btn small" onClick=${handleDelete}>Delete</button>
        <button class="btn small" onClick=${handleRippleDelete}>Ripple delete</button>
        <span style=${{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <button class="btn small" onClick=${() => setPxPerSecond(p => Math.max(10, p - 10))}>-</button>
          <span class="small">Zoom</span>
          <button class="btn small" onClick=${() => setPxPerSecond(p => p + 10)}>+</button>
        </span>
        <button class="btn small" style=${{ marginLeft: 'auto' }} onClick=${handleRender} disabled=${rendering}>
          ${rendering ? 'Rendering...' : 'Render'}
        </button>
      </div>
      <div style=${styles.libraryStrip}>
        ${library.map(item => html`
          <div 
            key=${item.src} 
            class=${selectedLib === item.src ? 'chip on' : 'chip'} 
            style=${styles.libItem(selectedLib === item.src)}
            onClick=${() => setSelectedLib(item.src)}
          >
            ${item.label}
          </div>
        `)}
      </div>
      <div style=${styles.timelineArea} ref=${containerRef}>
        <div style=${{ width: `${width}px`, position: 'relative' }}>
          <div style=${styles.ruler} onClick=${handleRulerClick}>
            ${ticks.map(s => html`
              <div key=${s} style=${styles.tick(s)}></div>
              <div key=${`l${s}`} style=${styles.tickLabel(s)}>${s}s</div>
            `)}
          </div>
          ${state.tracks.map((track, tIdx) => html`
            <div key=${tIdx} style=${styles.track}>
              ${track.clips.map(clip => {
                const isSel = selectedClip && selectedClip.track === tIdx && selectedClip.id === clip.id;
                return html`
                  <div 
                    key=${clip.id} 
                    style=${{ ...styles.clip(isSel), left: `${clip.start * pxPerSecond}px`, width: `${clip.dur * pxPerSecond}px` }}
                    onClick=${(e) => handleClipClick(e, tIdx, clip.id)}
                    onPointerDown=${(e) => handleClipPointerDown(e, tIdx, clip.id, clip)}
                  >
                    <span style=${{ pointerEvents: 'none' }}>${clip.label}</span>
                    <div style=${{ ...styles.edge('left'), left: '0' }} onPointerDown=${(e) => handleEdgePointerDown(e, tIdx, clip.id, 'left')}></div>
                    <div style=${{ ...styles.edge('right'), right: '0' }} onPointerDown=${(e) => handleEdgePointerDown(e, tIdx, clip.id, 'right')}></div>
                  </div>
                `;
              })}
            </div>
          `)}
          <div style=${{ ...styles.playhead, left: `${state.playhead * pxPerSecond}px` }}></div>
        </div>
      </div>
      ${problems.length > 0 && html`
        <div style=${styles.problems}>
          ${problems.map((p, i) => html`<div key=${i}>${p}</div>`)}
        </div>
      `}
    </div>
  `;
}
