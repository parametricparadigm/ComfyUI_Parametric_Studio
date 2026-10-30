import assert from 'node:assert';
import {
  createTimeline,
  addTrack,
  addClip,
  moveClip,
  trimClip,
  splitAt,
  removeClip,
  setPlayhead,
  duration,
  toEDL,
  validateEDL
} from './timeline_core.js';

// 1. createTimeline
const s0 = createTimeline();
assert.strictEqual(s0.fps, 24);
assert.strictEqual(s0.playhead, 0);
assert.strictEqual(s0.tracks.length, 2);
assert.strictEqual(s0.tracks[0].id, 'V1');
assert.strictEqual(s0.tracks[1].id, 'A1');

// 2. addTrack
const s1 = addTrack(s0, 'video');
assert.strictEqual(s1.tracks.length, 3);
assert.strictEqual(s1.tracks[2].id, 'V2');

// 3. addClip basic
const s2 = addClip(s1, 'V1', { src: 'a.mp4', label: 'A', dur: 2, start: 0 });
assert.strictEqual(s2.tracks[0].clips.length, 1);
assert.strictEqual(s2.tracks[0].clips[0].id, 'c1');
assert.strictEqual(s2.tracks[0].clips[0].start, 0);

// 4. addClip default start (end of track)
const s3 = addClip(s2, 'V1', { src: 'b.mp4', label: 'B', dur: 1 });
assert.strictEqual(s3.tracks[0].clips[1].start, 2);

// 5. addClip overlap move
const s4 = addClip(s3, 'V1', { src: 'c.mp4', label: 'C', dur: 1, start: 1 });
// Overlaps with B (2-3)? No. Overlaps with A (0-2)? Yes. Moved to end of A (2).
// Wait, B is at 2. So C at 2 overlaps B. Moved to end of B (3).
assert.strictEqual(s4.tracks[0].clips[2].start, 3);

// 6. addClip invalid dur
const s5 = addClip(s4, 'V1', { src: 'd.mp4', label: 'D', dur: 0 });
assert.strictEqual(s5, s4);

// 7. duration
assert.strictEqual(duration(s4), 4); // A(0-2), B(2-3), C(3-4)

// 8. setPlayhead clamp
const s6 = setPlayhead(s4, 100);
assert.strictEqual(s6.playhead, 4);
const s7 = setPlayhead(s4, -10);
assert.strictEqual(s7.playhead, 0);

// 9. moveClip basic
const s8 = moveClip(s4, 'c1', 10);
const v1Clips = s8.tracks[0].clips;
const c1 = v1Clips.find(c => c.id === 'c1');
assert.strictEqual(c1.start, 10);

// 10. moveClip snap
// s4: A(0-2), B(2-3), C(3-4). Playhead 0.
// Move C (3-4) to 2.5. Snap to B end (3) or B start (2)?
// 2.5 is 0.5 from 2 and 0.5 from 3. No snap if snap=0.1.
// Let's try moving C to 2.9. Snap to 3 (dist 0.1).
const s9 = moveClip(s4, 'c3', 2.9, { snap: 0.1 });
const c3 = s9.tracks[0].clips.find(c => c.id === 'c3');
assert.strictEqual(c3.start, 3); // Snapped to 3? Wait, 3 is occupied by C originally?
// C is 3-4. Moving C to 3 is same position.
// Let's move A (0-2) to 2.9.
const s10 = moveClip(s4, 'c1', 2.9, { snap: 0.1 });
const c1New = s10.tracks[0].clips.find(c => c.id === 'c1');
// A moves to 3 (snapped from 2.9 to 3).
// Does A(3-5) overlap B(2-3)? No. Overlap C(3-4)? Yes.
// So moveClip should return s4 (same state) because of overlap.
assert.strictEqual(s10, s4);

// 11. moveClip to another track
const s11 = addTrack(s4, 'video'); // V2
const s12 = moveClip(s11, 'c1', 0, { trackId: 'V2' });
assert.strictEqual(s12.tracks[2].clips.length, 1);
assert.strictEqual(s12.tracks[0].clips.length, 2); // A removed from V1

// 12. trimClip start
const s13 = trimClip(s4, 'c1', 'start', 0.5);
const c1Trim = s13.tracks[0].clips.find(c => c.id === 'c1');
assert.strictEqual(c1Trim.start, 0.5);
assert.strictEqual(c1Trim.dur, 1.5);
assert.strictEqual(c1Trim.in, 0.5);

// 13. trimClip end
const s14 = trimClip(s4, 'c1', 'end', -0.5);
const c1TrimEnd = s14.tracks[0].clips.find(c => c.id === 'c1');
assert.strictEqual(c1TrimEnd.dur, 1.5);

// 14. trimClip min dur
const s15 = trimClip(s4, 'c1', 'end', -1.95); // dur 2 - 1.95 = 0.05 < 0.1
assert.strictEqual(s15, s4);

// 15. trimClip start limit (in < 0)
const s16 = trimClip(s4, 'c1', 'start', -0.1); // in 0 - 0.1 = -0.1
assert.strictEqual(s16, s4);

// 16. splitAt
const s17 = splitAt(s4, 'c1', 1); // Split A(0-2) at 1
assert.strictEqual(s17.tracks[0].clips.length, 4);
const c1Split = s17.tracks[0].clips.find(c => c.id === 'c1');
const c4 = s17.tracks[0].clips.find(c => c.id === 'c4');
assert.strictEqual(c1Split.dur, 1);
assert.strictEqual(c4.start, 1);
assert.strictEqual(c4.dur, 1);
assert.strictEqual(c4.in, 1);

// 17. splitAt bounds
const s18 = splitAt(s4, 'c1', 0.05); // Too close to start
assert.strictEqual(s18, s4);
const s19 = splitAt(s4, 'c1', 1.95); // Too close to end
assert.strictEqual(s19, s4);

// 20. removeClip
const s20 = removeClip(s4, 'c1');
assert.strictEqual(s20.tracks[0].clips.length, 2);

// 21. removeClip ripple
const s21 = removeClip(s4, 'c1', { ripple: true });
const c2Ripple = s21.tracks[0].clips.find(c => c.id === 'c2');
assert.strictEqual(c2Ripple.start, 0); // B was at 2, shifted by 2

// 22. toEDL
const edl = toEDL(s4);
assert.strictEqual(edl.fps, 24);
assert.strictEqual(edl.duration, 4);
assert.strictEqual(edl.tracks.length, 1); // Only V1 has clips
assert.strictEqual(edl.tracks[0].kind, 'video');
assert.strictEqual(edl.tracks[0].clips.length, 3);
assert.strictEqual(edl.tracks[0].clips[0].start, 0);
assert.strictEqual(edl.tracks[0].clips[1].start, 2);
assert.strictEqual(edl.tracks[0].clips[2].start, 3);

// 23. validateEDL valid
const validEdl = {
  fps: 24,
  duration: 4,
  tracks: [
    {
      kind: 'video',
      clips: [
        { src: 'a.mp4', start: 0, dur: 2, in: 0 },
        { src: 'b.mp4', start: 2, dur: 1, in: 0 }
      ]
    }
  ]
};
const probs = validateEDL(validEdl);
assert.strictEqual(probs.length, 0);

// 24. validateEDL invalid fps
const badFps = { ...validEdl, fps: 0 };
const probs2 = validateEDL(badFps);
assert.ok(probs2.some(p => p.includes('fps')));

// 25. validateEDL overlap
const badOverlap = {
  fps: 24,
  duration: 4,
  tracks: [
    {
      kind: 'video',
      clips: [
        { src: 'a.mp4', start: 0, dur: 2, in: 0 },
        { src: 'b.mp4', start: 1, dur: 1, in: 0 }
      ]
    }
  ]
};
const probs3 = validateEDL(badOverlap);
assert.ok(probs3.some(p => p.includes('overlap')));

console.log('ok');
