export function createTimeline({ fps = 24 } = {}) {
  return {
    fps,
    playhead: 0,
    tracks: [
      { id: 'V1', kind: 'video', clips: [] },
      { id: 'A1', kind: 'audio', clips: [] }
    ]
  };
}

export function duration(state) {
  let max = 0;
  for (const track of state.tracks) {
    for (const clip of track.clips) {
      const end = clip.start + clip.dur;
      if (end > max) max = end;
    }
  }
  return max;
}

function nextTrackId(state, kind) {
  const prefix = kind === 'video' ? 'V' : 'A';
  let max = 0;
  for (const track of state.tracks) {
    if (track.kind === kind) {
      const num = parseInt(track.id.slice(1), 10);
      if (num > max) max = num;
    }
  }
  return `${prefix}${max + 1}`;
}

export function addTrack(state, kind) {
  if (kind !== 'video' && kind !== 'audio') return state;
  const id = nextTrackId(state, kind);
  const newTrack = { id, kind, clips: [] };
  return {
    ...state,
    tracks: [...state.tracks, newTrack]
  };
}

function nextClipId(state) {
  let max = 0;
  for (const track of state.tracks) {
    for (const clip of track.clips) {
      const num = parseInt(clip.id.slice(1), 10);
      if (num > max) max = num;
    }
  }
  return `c${max + 1}`;
}

function trackEnd(track) {
  let max = 0;
  for (const clip of track.clips) {
    const end = clip.start + clip.dur;
    if (end > max) max = end;
  }
  return max;
}

function overlaps(a, b) {
  return a.start < b.start + b.dur && b.start < a.start + a.dur;
}

export function addClip(state, trackId, { src, label, dur, in: inPoint = 0, start }) {
  if (dur <= 0) return state;
  const trackIdx = state.tracks.findIndex(t => t.id === trackId);
  if (trackIdx === -1) return state;
  
  const track = state.tracks[trackIdx];
  let placedStart = start !== undefined ? start : trackEnd(track);
  
  let changed = true;
  while (changed) {
    changed = false;
    for (const clip of track.clips) {
      const newClip = { id: '', src, label, start: placedStart, dur, in: inPoint };
      if (overlaps(newClip, clip)) {
        const clipEnd = clip.start + clip.dur;
        if (clipEnd > placedStart) {
          placedStart = clipEnd;
          changed = true;
        }
      }
    }
  }
  
  const newClip = {
    id: nextClipId(state),
    src,
    label,
    start: placedStart,
    dur,
    in: inPoint
  };
  
  const newTracks = state.tracks.map((t, i) => {
    if (i === trackIdx) {
      return { ...t, clips: [...t.clips, newClip] };
    }
    return t;
  });
  
  return { ...state, tracks: newTracks };
}

export function moveClip(state, clipId, newStart, { snap = 0.1, trackId } = {}) {
  let clipFound = null;
  let origTrackIdx = -1;
  
  for (let i = 0; i < state.tracks.length; i++) {
    const track = state.tracks[i];
    const ci = track.clips.findIndex(c => c.id === clipId);
    if (ci !== -1) {
      clipFound = track.clips[ci];
      origTrackIdx = i;
      break;
    }
  }
  
  if (!clipFound) return state;
  
  let targetTrackIdx = origTrackIdx;
  if (trackId) {
    targetTrackIdx = state.tracks.findIndex(t => t.id === trackId);
    if (targetTrackIdx === -1) return state;
    if (state.tracks[targetTrackIdx].kind !== state.tracks[origTrackIdx].kind) return state;
  }
  
  let finalStart = Math.max(0, newStart);
  
  const targetTrack = state.tracks[targetTrackIdx];
  const snapPoints = [state.playhead];
  
  for (const clip of targetTrack.clips) {
    if (clip.id === clipId && targetTrackIdx === origTrackIdx) continue;
    snapPoints.push(clip.start);
    snapPoints.push(clip.start + clip.dur);
  }
  
  let bestSnap = finalStart;
  let bestDist = snap;
  for (const point of snapPoints) {
    const dist = Math.abs(finalStart - point);
    if (dist < bestDist) {
      bestDist = dist;
      bestSnap = point;
    }
  }
  finalStart = bestSnap;
  
  const movedClip = { ...clipFound, start: finalStart };
  for (const clip of targetTrack.clips) {
    if (clip.id === clipId && targetTrackIdx === origTrackIdx) continue;
    if (overlaps(movedClip, clip)) {
      return state;
    }
  }
  
  const newTracks = state.tracks.map((t, i) => {
    if (i === origTrackIdx) {
      const clips = t.clips.filter(c => c.id !== clipId);
      return { ...t, clips };
    }
    return t;
  });
  
  const targetTrackNew = newTracks[targetTrackIdx];
  const newClips = [...targetTrackNew.clips, movedClip];
  newTracks[targetTrackIdx] = { ...targetTrackNew, clips: newClips };
  
  return { ...state, tracks: newTracks };
}

export function trimClip(state, clipId, edge, delta) {
  let clipFound = null;
  let trackIdx = -1;
  
  for (let i = 0; i < state.tracks.length; i++) {
    const track = state.tracks[i];
    const ci = track.clips.findIndex(c => c.id === clipId);
    if (ci !== -1) {
      clipFound = track.clips[ci];
      trackIdx = i;
      break;
    }
  }
  
  if (!clipFound) return state;
  
  const track = state.tracks[trackIdx];
  let newClip = { ...clipFound };
  
  if (edge === 'start') {
    const newStart = clipFound.start + delta;
    const newIn = clipFound.in + delta;
    const newDur = clipFound.dur - delta;
    
    if (newDur < 0.1) return state;
    if (newIn < 0) return state;
    if (newStart < 0) return state;
    
    newClip.start = newStart;
    newClip.in = newIn;
    newClip.dur = newDur;
    
    for (const clip of track.clips) {
      if (clip.id === clipId) continue;
      if (overlaps(newClip, clip)) return state;
    }
  } else if (edge === 'end') {
    const newDur = clipFound.dur + delta;
    if (newDur < 0.1) return state;
    
    newClip.dur = newDur;
    
    for (const clip of track.clips) {
      if (clip.id === clipId) continue;
      if (overlaps(newClip, clip)) return state;
    }
  } else {
    return state;
  }
  
  const newTracks = state.tracks.map((t, i) => {
    if (i === trackIdx) {
      const clips = t.clips.map(c => c.id === clipId ? newClip : c);
      return { ...t, clips };
    }
    return t;
  });
  
  return { ...state, tracks: newTracks };
}

export function splitAt(state, clipId, t) {
  let clipFound = null;
  let trackIdx = -1;
  let clipIdx = -1;
  
  for (let i = 0; i < state.tracks.length; i++) {
    const track = state.tracks[i];
    const ci = track.clips.findIndex(c => c.id === clipId);
    if (ci !== -1) {
      clipFound = track.clips[ci];
      trackIdx = i;
      clipIdx = ci;
      break;
    }
  }
  
  if (!clipFound) return state;
  
  const rel = t - clipFound.start;
  if (rel <= 0.1 || rel >= clipFound.dur - 0.1) return state;
  
  const firstDur = rel;
  const secondDur = clipFound.dur - rel;
  
  const first = { ...clipFound, dur: firstDur };
  const second = {
    id: nextClipId(state),
    src: clipFound.src,
    label: clipFound.label,
    start: clipFound.start + firstDur,
    dur: secondDur,
    in: clipFound.in + firstDur
  };
  
  const track = state.tracks[trackIdx];
  const newClips = [...track.clips];
  newClips[clipIdx] = first;
  newClips.splice(clipIdx + 1, 0, second);
  
  const newTracks = state.tracks.map((t, i) => {
    if (i === trackIdx) {
      return { ...t, clips: newClips };
    }
    return t;
  });
  
  return { ...state, tracks: newTracks };
}

export function removeClip(state, clipId, { ripple = false } = {}) {
  let clipFound = null;
  let trackIdx = -1;
  
  for (let i = 0; i < state.tracks.length; i++) {
    const track = state.tracks[i];
    const ci = track.clips.findIndex(c => c.id === clipId);
    if (ci !== -1) {
      clipFound = track.clips[ci];
      trackIdx = i;
      break;
    }
  }
  
  if (!clipFound) return state;
  
  const track = state.tracks[trackIdx];
  let newClips = track.clips.filter(c => c.id !== clipId);
  
  if (ripple) {
    const shift = clipFound.dur;
    newClips = newClips.map(c => {
      if (c.start > clipFound.start) {
        return { ...c, start: c.start - shift };
      }
      return c;
    });
  }
  
  const newTracks = state.tracks.map((t, i) => {
    if (i === trackIdx) {
      return { ...t, clips: newClips };
    }
    return t;
  });
  
  return { ...state, tracks: newTracks };
}

export function setPlayhead(state, t) {
  const maxT = duration(state);
  const clamped = Math.max(0, Math.min(t, maxT));
  return { ...state, playhead: clamped };
}

export function toEDL(state) {
  const tracks = state.tracks
    .filter(t => t.clips.length > 0)
    .map(t => ({
      kind: t.kind,
      clips: t.clips
        .slice()
        .sort((a, b) => a.start - b.start)
        .map(c => ({ src: c.src, start: c.start, dur: c.dur, in: c.in }))
    }));
  
  return {
    fps: state.fps,
    duration: duration(state),
    tracks
  };
}

export function validateEDL(edl) {
  const problems = [];
  
  if (typeof edl.fps !== 'number' || edl.fps <= 0) {
    problems.push('fps must be > 0');
  }
  
  if (!Array.isArray(edl.tracks)) {
    problems.push('tracks must be an array');
    return problems;
  }
  
  const validKinds = ['video', 'audio'];
  
  for (const track of edl.tracks) {
    if (!validKinds.includes(track.kind)) {
      problems.push(`invalid track kind: ${track.kind}`);
    }
    
    if (!Array.isArray(track.clips)) continue;
    
    const sorted = track.clips.slice().sort((a, b) => a.start - b.start);
    
    for (let i = 0; i < sorted.length; i++) {
      const clip = sorted[i];
      
      if (typeof clip.src !== 'string') {
        problems.push(`clip ${i} in track ${track.kind} missing src`);
      }
      
      if (typeof clip.start !== 'number' || clip.start < 0) {
        problems.push(`clip ${i} in track ${track.kind} has invalid start`);
      }
      
      if (typeof clip.dur !== 'number' || clip.dur <= 0) {
        problems.push(`clip ${i} in track ${track.kind} has invalid dur`);
      }
      
      if (typeof clip.in !== 'number' || clip.in < 0) {
        problems.push(`clip ${i} in track ${track.kind} has invalid in`);
      }
      
      if (i > 0) {
        const prev = sorted[i - 1];
        if (prev.start + prev.dur > clip.start) {
          problems.push(`overlap in track ${track.kind} at clip ${i}`);
        }
      }
    }
  }
  
  return problems;
}
