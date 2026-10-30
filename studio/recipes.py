"""Recipes: multi-step chains that really run. Each step is a studio goal (the same internals as POST /api/generate), a local ComfyUI template (the same build as the AI edit tools) or a small ffmpeg step, and a step's output is uploaded as the next step's input.
One worker thread runs one recipe at a time. Before every GPU step the free-VRAM rule is checked (peak + 4 GiB, unloading ComfyUI when short); after every GPU step ComfyUI unloads, so each step starts cold and the measured figures stay honest.
Run state is a JSON file next to the outputs, so a server restart does not lose finished runs. recipes.json holds the recipes; a recipe only says "tested" when it rendered on this box and its media and numbers are recorded there."""
import asyncio, json, os, queue, re, shutil, subprocess, sys, threading, time, urllib.parse, urllib.request, uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from studio import sfw

HERE = Path(__file__).resolve().parent; DATA = HERE / "recipes.json"; HEADROOM = 4.0; VRAM_WAIT = 600; POLL = 2.0; STEP_LIMIT = 1800
FPS = 24; FF_TIMEOUT = 600
class StepError(Exception): pass
class Cancelled(Exception): pass

def load():
    return json.load(open(DATA))
def _srv():
    """The running server module, whichever way it was started (python -m studio.server makes it __main__)."""
    m = sys.modules.get("__main__")
    if m is not None and hasattr(m, "_graph") and hasattr(m, "JOBS"): return m
    import studio.server as m
    return m
def _root():
    p = Path(_srv().OUTPUT) / "studio_recipes"; p.mkdir(parents=True, exist_ok=True); return p
def _fill(text, values):
    """{key} placeholders the recipe declares, and nothing else: prompts may hold other braces."""
    return re.sub(r"\{([a-z_][a-z0-9_]*)\}", lambda m: str(values[m.group(1)]) if m.group(1) in values else m.group(0), str(text))
def field_defaults(rec): return {f["key"]: f.get("default", "") for f in rec.get("fields", [])}

# ---------- ffmpeg steps. Pure functions: paths in, paths and facts out. No ComfyUI and no GPU, so tests run them for real.
def _ff(args, timeout=FF_TIMEOUT):
    r = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0: raise StepError("ffmpeg failed: " + (r.stderr or "").strip()[-300:])
    return r
def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate:format=duration", "-of", "json", str(path)], capture_output=True, text=True, timeout=30)
    d = json.loads(r.stdout or "{}"); st = d.get("streams") or []; v = next((s for s in st if s.get("codec_type") == "video"), None)
    return {"duration": float((d.get("format") or {}).get("duration") or 0), "width": int(v["width"]) if v else 0, "height": int(v["height"]) if v else 0, "video": bool(v), "audio": any(s.get("codec_type") == "audio" for s in st)}
ENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]; AENC = ["-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
def _shape(i, w, h): return f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps={FPS},format=yuv420p"
def _even(n): return int(n) - int(n) % 2
def frame(clip, out, which="last"):
    """One frame of a clip as a picture: the first, or the last one (the next clip's start in a long take)."""
    if which == "first": _ff(["-i", str(clip), "-frames:v", "1", "-update", "1", str(out)])
    else: _ff(["-sseof", "-0.25", "-i", str(clip), "-update", "1", str(out)])
    if not Path(out).exists(): raise StepError("could not read a frame from the clip")
    return {"file": str(out), "kind": "image", "note": f"{which} frame"}
def join(clips, out, crossfade=0.0, keep_audio=True):
    """Clips one after another, in the first clip's size. crossfade 0 is a hard cut, which is invisible when a clip starts on the frame the last one ended on."""
    infos = [probe(c) for c in clips]; w, h = _even(infos[0]["width"]), _even(infos[0]["height"]); keep_audio = keep_audio and any(i["audio"] for i in infos); args = []
    for c in clips: args += ["-i", str(c)]
    parts = []; n = len(clips)
    for i, inf in enumerate(infos):
        parts.append(_shape(i, w, h) + f"[v{i}]")
        if keep_audio: parts.append((f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo[a{i}]") if inf["audio"] else f"anullsrc=r=48000:cl=stereo,atrim=0:{inf['duration']:.3f}[a{i}]")
    if crossfade > 0 and n > 1:
        vl, al, t = "v0", "a0", infos[0]["duration"]
        for i in range(1, n):
            t -= crossfade; parts.append(f"[{vl}][v{i}]xfade=transition=fade:duration={crossfade}:offset={t:.3f}[vx{i}]"); vl = f"vx{i}"
            if keep_audio: parts.append(f"[{al}][a{i}]acrossfade=d={crossfade}[ax{i}]"); al = f"ax{i}"
            t += infos[i]["duration"]
        vout, aout = f"[{vl}]", f"[{al}]"
    else:
        ins = "".join(f"[v{i}]" + (f"[a{i}]" if keep_audio else "") for i in range(n)); parts.append(ins + f"concat=n={n}:v=1:a={1 if keep_audio else 0}[vc]" + ("[ac]" if keep_audio else "")); vout, aout = "[vc]", "[ac]"
    _ff(args + ["-filter_complex", ";".join(parts), "-map", vout] + (["-map", aout] if keep_audio else []) + ENC + (AENC if keep_audio else []) + [str(out)])
    p = probe(out); return {"file": str(out), "kind": "video", "note": f"{n} clips joined, {p['duration']:.1f} s", "facts": {"seconds": round(p["duration"], 2), "crossfade": crossfade}}
def decode_mono(path, sr=22050):
    import numpy as np
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"], capture_output=True, timeout=120)
    if r.returncode != 0: raise StepError("could not read the audio")
    return np.frombuffer(r.stdout, dtype=np.float32)
def beat_grid(x, sr=22050, hop=512, n=2048, tightness=120.0):
    """Tempo and beat times of a mono signal: spectral-flux onsets, tempo from their autocorrelation with a soft preference near 120 BPM, then the dynamic-programming beat tracker (Ellis 2007). Music 3 ignores a BPM asked for in the caption about one time in six, so the song is measured, not trusted.
    Returns (bpm, beats in seconds, index of the likely downbeat among the first four, onset envelope)."""
    import numpy as np
    if len(x) < n * 8: return 120.0, [], 0, np.zeros(1)
    w = np.hanning(n); nfr = 1 + (len(x) - n) // hop; idx = np.arange(n)[None, :] + hop * np.arange(nfr)[:, None]
    mag = np.log1p(np.abs(np.fft.rfft(x[idx] * w, axis=1)) * 10); flux = np.maximum(0, np.diff(mag, axis=0)).sum(axis=1); fps = sr / hop
    k = int(fps * 0.5) | 1; env = np.maximum(0, flux - np.convolve(flux, np.ones(k) / k, mode="same")); s = env.std() or 1.0; env = env / s
    if not env.any(): return 120.0, [], 0, env
    ac = np.correlate(env, env, "full")[len(env) - 1:]; lo, hi = int(fps * 60 / 200), min(int(fps * 60 / 50), len(ac) - 1); lags = np.arange(lo, hi)
    score = ac[lo:hi] * np.exp(-0.5 * (np.log2((60 * fps / lags) / 120.0) / 1.0) ** 2); lag = int(lags[int(np.argmax(score))])
    if 0 < lag - lo < len(score) - 1:                                                              # parabolic refinement: a 43 Hz grid is too coarse for tempo over a whole song
        a, b, c = ac[lag - 1], ac[lag], ac[lag + 1]; d = a - 2 * b + c; lag_f = lag + (0.5 * (a - c) / d if d else 0.0)
    else: lag_f = float(lag)
    bpm = 60 * fps / lag_f; period = lag_f; win = np.arange(-int(round(2 * period)), -int(round(period / 2))); pen = -tightness * np.log(-win / period) ** 2
    dp = env.copy(); back = -np.ones(len(env), dtype=int)
    for i in range(-win[0], len(env)):
        cand = dp[i + win] + pen; j = int(np.argmax(cand)); dp[i] = env[i] + cand[j]; back[i] = i + win[j]
    i = int(np.argmax(dp[-int(period * 2):])) + len(dp) - int(period * 2); path = []
    while i >= 0: path.append(i); i = back[i]
    fr = np.array(path[::-1]); keep = env[fr] > 0.05 * env.max(); fr = fr[np.argmax(keep):] if keep.any() else fr; beats = (fr + 1) * hop / sr + (n / 2) / sr                 # +1: flux at frame i is the change into i+1
    down = int(np.argmax([env[fr[o::4]].sum() for o in range(4)])) if len(fr) >= 8 else 0
    return float(bpm), [float(t) for t in beats], down, env
def _best_window(x, sr, t_candidates, total):
    """The start among the candidates whose window of `total` seconds is loudest: the song's hook, not its intro."""
    import numpy as np
    if not t_candidates: return 0.0
    hop = sr // 4; rms = np.sqrt(np.convolve(x.astype(np.float64) ** 2, np.ones(hop) / hop, mode="same")[::hop] + 1e-12); cum = np.concatenate([[0.0], np.cumsum(rms)]); best, bt = -1.0, t_candidates[0]
    for t in t_candidates:
        a, b = int(t * 4), min(int((t + total) * 4), len(rms))
        if b <= a or b - a < total * 4 * 0.98: continue
        v = (cum[b] - cum[a]) / (b - a)
        if v > best: best, bt = v, t
    return float(bt)
FITS = (16, 12, 8, 7, 6, 5, 4, 3, 2, 1)
def plan_cuts(beats, down, durations, total_max=None, x=None, sr=22050, section="energy", head=0.25):
    """Where each shot starts and ends, on beats. Each shot gets the largest length in beats (8, then 7, 6, 5, 4...) that its clip can fill. -> list of {clip, in, frames, beat}, start time in the song, end time."""
    usable = [max(0.0, d - head) for d in durations]; beat = (beats[-1] - beats[0]) / (len(beats) - 1) if len(beats) > 1 else 0.5
    lens = [next((f for f in FITS if f * beat <= u), 1) for u in usable]
    if total_max:
        while sum(lens) * beat > total_max and len(lens) > 1: lens = lens[:-1]
    total = sum(lens) * beat; down_beats = list(range(down, len(beats), 4)) or [0]; last_ok = [i for i in down_beats if beats[i] + total <= beats[-1] + beat]
    if not last_ok: start_i = down_beats[0]
    elif section == "energy" and x is not None: t0 = _best_window(x, sr, [beats[i] for i in last_ok], total); start_i = next(i for i in last_ok if beats[i] == t0)
    else: start_i = last_ok[0]
    shots, i, t0 = [], start_i, beats[start_i]; frame_at = lambda t: int(round((t - t0) * FPS))
    for c, L in enumerate(lens):
        a, b = i, min(i + L, len(beats) - 1); ta, tb = beats[a], beats[b] if b > a else beats[a] + L * beat; fr = frame_at(tb) - frame_at(ta); shots.append({"clip": c, "in": round(min(head, max(0.0, durations[c] - fr / FPS)), 3), "frames": fr, "beats": L, "at": round(ta - t0, 3)}); i = b
    end = shots[-1]["at"] + shots[-1]["frames"] / FPS
    return shots, t0, t0 + end
def master_filter(duration, fade_in=0.04, fade_out=1.0, lufs=-14):
    """Music 3 renders hot (true peak at or above 0 dBTP in the owner's tests), and a section cut from a song ends abruptly: a short fade and loudness normalization fix both."""
    return f"afade=t=in:st=0:d={fade_in},afade=t=out:st={max(0.0, duration - fade_out):.3f}:d={fade_out},loudnorm=I={lufs}:TP=-1.5:LRA=11,aresample=48000"
def beat_cut(clips, audio, out, total_max=None, section="energy", head=0.25, clip_audio_db=None):
    """Cut clips to the beat of a song, in order, hard cuts on measured beats, shots starting on a likely downbeat, and lay the song under them. Frame-exact at 24 fps."""
    x = decode_mono(audio); bpm, beats, down, _env = beat_grid(x); infos = [probe(c) for c in clips]; durs = [i["duration"] for i in infos]
    if len(beats) < 4: raise StepError("no beat found in the song")
    shots, t0, t1 = plan_cuts(beats, down, durs, total_max, x, 22050, section, head); w, h = _even(infos[0]["width"]), _even(infos[0]["height"]); args = []
    for c in clips[:len(shots)]: args += ["-i", str(c)]
    args += ["-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", str(audio)]; ai = len(shots); parts = []
    for s in shots: parts.append(f"[{s['clip']}:v]trim=start={s['in']},setpts=PTS-STARTPTS,scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps={FPS},trim=end_frame={s['frames']},setpts=PTS-STARTPTS,format=yuv420p[v{s['clip']}]")
    parts.append("".join(f"[v{s['clip']}]" for s in shots) + f"concat=n={len(shots)}:v=1:a=0[vo]"); dur = t1 - t0
    if clip_audio_db is not None and any(infos[s["clip"]]["audio"] for s in shots):
        lanes = []
        for s in shots:
            if infos[s["clip"]]["audio"]: parts.append(f"[{s['clip']}:a]atrim=start={s['in']}:duration={s['frames'] / FPS:.3f},asetpts=PTS-STARTPTS,volume={clip_audio_db}dB,adelay={int(s['at'] * 1000)}:all=1[c{s['clip']}]"); lanes.append(f"[c{s['clip']}]")
        parts.append(f"[{ai}:a]" + "".join(lanes) + f"amix=inputs={len(lanes) + 1}:normalize=0:duration=first,{master_filter(dur)}[ao]")
    else: parts.append(f"[{ai}:a]{master_filter(dur)}[ao]")
    _ff(args + ["-filter_complex", ";".join(parts), "-map", "[vo]", "-map", "[ao]"] + ENC + AENC + ["-shortest", str(out)])
    p = probe(out); facts = {"bpm": round(bpm, 1), "cuts_at": [s["at"] for s in shots], "beats_per_shot": [s["beats"] for s in shots], "song_from": round(t0, 2), "seconds": round(p["duration"], 2)}
    return {"file": str(out), "kind": "video", "note": f"{len(shots)} shots cut on the beat at {bpm:.0f} BPM, {p['duration']:.1f} s", "facts": facts}
def cut_between(clips, out, audio_from=0, pieces=None):
    """Cut between several takes of one moment at the same timecode, under one continuous sound: multi-camera editing of clips that share timing."""
    infos = [probe(c) for c in clips]; dur = min(i["duration"] for i in infos); n = len(clips); pieces = pieces or n * 2; w, h = _even(infos[0]["width"]), _even(infos[0]["height"]); cut = [int(round(dur * FPS * i / pieces)) for i in range(pieces + 1)]; args = []
    for c in clips: args += ["-i", str(c)]
    parts = []
    for p in range(pieces): parts.append(_shape(p % n, w, h) + f",trim=start_frame={cut[p]}:end_frame={cut[p + 1]},setpts=PTS-STARTPTS[p{p}]")
    parts.append("".join(f"[p{p}]" for p in range(pieces)) + f"concat=n={pieces}:v=1:a=0[vo]"); has = infos[audio_from]["audio"]
    if has: parts.append(f"[{audio_from}:a]atrim=0:{dur:.3f},asetpts=PTS-STARTPTS,{master_filter(dur, fade_out=0.4)}[ao]")
    _ff(args + ["-filter_complex", ";".join(parts), "-map", "[vo]"] + (["-map", "[ao]"] if has else []) + ENC + (AENC if has else []) + [str(out)])
    p = probe(out); return {"file": str(out), "kind": "video", "note": f"{pieces} cuts between {n} cameras on one sound track, {p['duration']:.1f} s", "facts": {"seconds": round(p["duration"], 2), "cuts_at": [round(c / FPS, 3) for c in cut[1:-1]]}}
def _ssim(a, b):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(a), "-i", str(b), "-lavfi", "ssim", "-f", "null", "-"], capture_output=True, text=True, timeout=60)
    m = re.search(r"All:([0-9.]+)", r.stderr or ""); return float(m.group(1)) if m else None
def loop_seam(clip, out, crossfade=0.5):
    """Make a clip loop: its tail fades into its head, so the last frame flows into the first. A generated first+last frame clip lands near its first frame, not on it, and this closes the gap; the loop is shorter by the fade. Reports SSIM across the seam, before and after: 1.0 is identical."""
    inf = probe(clip); D = inf["duration"]; X = min(crossfade, D / 3); tmp = Path(out).parent; first, last = tmp / (Path(out).stem + "_a.png"), tmp / (Path(out).stem + "_b.png"); frame(clip, first, "first"); frame(clip, last, "last"); raw = _ssim(first, last)
    parts = [f"[0:v]fps={FPS},format=yuv420p,split[a][b];[a]trim=start={X},setpts=PTS-STARTPTS[body];[b]trim=end={X},setpts=PTS-STARTPTS[head];[body][head]xfade=transition=fade:duration={X}:offset={D - 2 * X:.3f}[vo]"]
    if inf["audio"]: parts.append(f"[0:a]asplit[x][y];[x]atrim=start={X},asetpts=PTS-STARTPTS[bodya];[y]atrim=end={X},asetpts=PTS-STARTPTS[heada];[bodya][heada]acrossfade=d={X}[ao]")
    _ff(["-i", str(clip), "-filter_complex", ";".join(parts), "-map", "[vo]"] + (["-map", "[ao]"] if inf["audio"] else []) + ENC + (AENC if inf["audio"] else []) + [str(out)])
    a2, b2 = tmp / (Path(out).stem + "_c.png"), tmp / (Path(out).stem + "_d.png"); frame(out, a2, "first"); frame(out, b2, "last"); after = _ssim(a2, b2)
    for f in (first, last, a2, b2): Path(f).unlink(missing_ok=True)
    p = probe(out); facts = {"seam_ssim_before": round(raw, 4) if raw is not None else None, "seam_ssim_after": round(after, 4) if after is not None else None, "seconds": round(p["duration"], 2), "crossfade": X}
    return {"file": str(out), "kind": "video", "note": f"loop of {p['duration']:.1f} s; seam SSIM {facts['seam_ssim_before']} before, {facts['seam_ssim_after']} after", "facts": facts}
def _label(text):
    t = re.sub(r"[^A-Za-z0-9 +.,()/-]", "", str(text))[:40]; return t.replace(":", " ").replace("'", "")
def compare(clips, out, labels=None, audio_from=None, height=None, mode="grid"):
    """Clips next to each other with their names on them, cut to the shortest. Two: side by side (or a split wipe with mode=split). Three: a row. Four: two rows. Falls back to no labels if ffmpeg has no font."""
    infos = [probe(c) for c in clips]; n = len(clips); w0, h0 = _even(infos[0]["width"]), _even(infos[0]["height"]); labels = labels or []
    if mode == "split": cw, ch = w0, h0
    else: ch = _even(height or (h0 if n == 2 else min(h0, 540))); cw = _even(ch * w0 / h0)
    dur = min(i["duration"] for i in infos); args = []
    for c in clips: args += ["-i", str(c)]
    def build(with_text):
        parts = []
        for i in range(n):
            tx = ""
            if with_text and i < len(labels) and labels[i]: tx = f",drawtext=font=sans:fontsize={max(16, ch // 26)}:text='{_label(labels[i])}':fontcolor=white:borderw=2:bordercolor=black@0.8:x={'(w-text_w-24)' if mode == 'split' and i == 1 else '24'}:y=h-text_h-22"
            parts.append(_shape(i, cw, ch) + f",trim=duration={dur:.3f},setpts=PTS-STARTPTS{tx}[v{i}]")
        if mode == "split" and n == 2: parts.append(f"[v0]crop={cw // 2}:{ch}:0:0[l];[v1]crop={cw - cw // 2}:{ch}:{cw // 2}:0[r];[l][r]hstack=2,drawbox=x={cw // 2 - 1}:y=0:w=2:h={ch}:color=0xf5c518:t=fill[vo]")
        elif n == 1: parts.append("[v0]null[vo]")
        elif n == 4: parts.append("".join(f"[v{i}]" for i in range(4)) + "xstack=inputs=4:layout=0_0|w0_0|0_h0|w0_h0[vo]")
        else: parts.append("".join(f"[v{i}]" for i in range(n)) + f"hstack=inputs={n}[vo]")
        ai = audio_from if audio_from is not None and infos[audio_from]["audio"] else None
        if ai is not None: parts.append(f"[{ai}:a]atrim=0:{dur:.3f},asetpts=PTS-STARTPTS,aresample=48000[ao]")
        return ["-filter_complex", ";".join(parts), "-map", "[vo]"] + (["-map", "[ao]"] if ai is not None else []) + ENC + (AENC if ai is not None else []) + [str(out)]
    try: _ff(args + build(True))
    except StepError: _ff(args + build(False))
    p = probe(out); return {"file": str(out), "kind": "video", "note": f"{n} versions side by side, {p['duration']:.1f} s", "facts": {"seconds": round(p["duration"], 2)}}
def mux(video, audio, out, loudness=True):
    """Lay a sound file under a clip, trimmed to the clip, faded and normalized."""
    d = probe(video)["duration"]; flt = master_filter(d) if loudness else f"afade=t=out:st={max(0, d - 1):.3f}:d=1"
    _ff(["-i", str(video), "-i", str(audio), "-filter_complex", f"[1:a]atrim=0:{d:.3f},asetpts=PTS-STARTPTS,{flt}[ao]", "-map", "0:v", "-map", "[ao]", "-c:v", "copy"] + AENC + ["-movflags", "+faststart", "-shortest", str(out)])
    p = probe(out); return {"file": str(out), "kind": "video", "note": f"sound laid under the clip, {p['duration']:.1f} s", "facts": {"seconds": round(p["duration"], 2)}}


# ---------- one sentence to a short film: the local LLM writes the shot list first (it may be asleep during a render window, so a plan can be made ahead and passed in), then the chain is built from it
FILM_RULES = """You turn one sentence into a shot list for a short film. Answer with JSON only, no commentary.
Rules: 5 or 6 shots that tell the sentence from start to finish, each about 5 seconds. One main action per shot. One continuous shot, no cuts inside a shot. Describe what is present; do not use negatives. Say the character and the place in the same words every time.
Fictional adults only. No real people, no brands, no logos, no text on screen, no known characters or franchises. Safe for work. Give the character a look you can recognise from any angle: clothing, colours, silhouette; do not rely on the face. Give the character no name.
Schema: {"title": "2 to 4 words", "logline": "one sentence", "character": "one sentence: who they look like, clothing, colours, silhouette", "world": "one sentence: the place, the time, the light, the colour palette", "look": "one short phrase: film look, for example cinematic live-action, anamorphic, deep shadows", "music": {"style": "genre words", "mood": "one sentence on how it builds", "instruments": "main instruments", "bpm": 100}, "shots": [{"action": "one sentence, present tense, what we see happen", "shot": "extreme_wide|wide|medium|close_up|extreme_close_up", "camera": "dolly_in|dolly_out|orbit_left|orbit_right|crane_up|crane_down|pan_left|pan_right|tilt_up|tracking|handheld|locked", "sound": "the sounds in this shot, no music"}]}
The sentence: """
def _llm_candidates():
    from studio import llm_tiers as L
    out = []; first = L.endpoint()
    if first: out.append(first)
    for base in ("http://127.0.0.1:8002/v1", "http://127.0.0.1:8301/v1", "http://127.0.0.1:11434/v1"):
        if any(c["url"] == base for c in out): continue
        try: ids = L._models_at(base)
        except Exception: continue
        if ids: out.append({"url": base, "model": ids[0]})
    return out
def _asleep(base):
    try:
        with urllib.request.urlopen(base.rsplit("/v1", 1)[0] + "/is_sleeping", timeout=2) as r: return bool(json.load(r).get("is_sleeping"))
    except Exception: return False
def _chat(c, text, timeout=240):
    body = {"model": c["model"], "messages": [{"role": "user", "content": text}], "temperature": 0.6, "max_tokens": 3000, "chat_template_kwargs": {"enable_thinking": False}, "reasoning_effort": "none"}
    with urllib.request.urlopen(urllib.request.Request(c["url"] + "/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"}), timeout=timeout) as r: m = json.load(r)["choices"][0]["message"]
    return m.get("content") or m.get("reasoning") or ""
def _json_in(text):
    text = re.sub(r"<think>.*?</think>", "", str(text), flags=re.S); a, b = text.find("{"), text.rfind("}")
    return json.loads(text[a:b + 1]) if a >= 0 and b > a else None
SHOT_WORDS = ("extreme_wide", "wide", "medium", "close_up", "extreme_close_up"); CAM_ORDER = ("dolly_in", "tracking", "orbit_right", "close", "crane_up", "dolly_out")
def normalize_plan(raw, sentence, writer=""):
    """Whatever the writer returned, in a shape the chain can trust: 4 to 6 shots, known camera moves and framings, plain strings."""
    from studio.goals import CAMERA_MOVES
    raw = raw if isinstance(raw, dict) else {}; txt = lambda v, n=500: re.sub(r"\s+", " ", str(v or "")).strip()[:n]; m = raw.get("music") if isinstance(raw.get("music"), dict) else {}; shots = []
    for i, s in enumerate(x for x in (raw.get("shots") or []) if isinstance(x, dict) and txt(x.get("action"))):
        cam = txt(s.get("camera")); fr = txt(s.get("shot"))
        shots.append({"action": txt(s.get("action")), "shot": fr if fr in SHOT_WORDS else "wide", "camera": cam if cam in CAMERA_MOVES and cam != "dolly_zoom" else ("dolly_in" if i % 2 == 0 else "tracking"), "sound": txt(s.get("sound"), 200) or "quiet ambient sound of the place"})
    if len(shots) > 6: shots = shots[:6]
    if len(shots) < 4: return fallback_plan(sentence, "the writer's answer could not be used")
    try: bpm = max(70, min(150, int(m.get("bpm") or 100)))
    except Exception: bpm = 100
    return {"sentence": txt(sentence, 400), "title": txt(raw.get("title"), 60) or "Short film", "logline": txt(raw.get("logline"), 300) or txt(sentence, 300), "character": txt(raw.get("character")) or "a lone figure in a long dark coat and a wide brimmed hat", "world": txt(raw.get("world")) or "a quiet place at night, deep shadows and warm gold light", "look": txt(raw.get("look"), 160) or "cinematic live-action, anamorphic, deep shadows",
            "music": {"style": txt(m.get("style"), 120) or "cinematic orchestral", "mood": txt(m.get("mood"), 300) or "It starts quiet and builds to a wide, warm finish.", "instruments": txt(m.get("instruments"), 160) or "strings, piano, soft percussion", "bpm": bpm}, "shots": shots, "writer": writer}
def fallback_plan(sentence, why="no language model was reachable"):
    """A shot list from a fixed pattern, so the recipe still runs on a box with no LLM. It says so: the words are the sentence, repeated, not a written film."""
    t = re.sub(r"\s+", " ", str(sentence or "")).strip().rstrip("."); beats = [("We see the place first. " + t + ".", "extreme_wide", "crane_down"), (t + ", seen from behind.", "wide", "tracking"), (t + ", the moment it begins.", "medium", "dolly_in"), (t + ", a detail in close view.", "close_up", "orbit_right"), (t + ", at its height.", "wide", "orbit_left"), (t + ", the last image.", "extreme_wide", "dolly_out")]
    return {"sentence": t, "title": "Short film", "logline": t, "character": "a lone figure in a long dark coat and a wide brimmed hat", "world": "the place the sentence describes, deep shadows and warm gold light", "look": "cinematic live-action, anamorphic, deep shadows", "music": {"style": "cinematic orchestral", "mood": "It starts quiet and builds to a wide, warm finish.", "instruments": "strings, piano, soft percussion", "bpm": 100}, "shots": [{"action": a, "shot": f, "camera": c, "sound": "quiet ambient sound of the place"} for a, f, c in beats], "writer": f"fixed pattern ({why})"}
def plan_film(sentence):
    """The LLM's shot list. Skips a server that is asleep (a render window holds the card); falls back to a fixed pattern and says so."""
    tried = []
    for c in _llm_candidates():
        if _asleep(c["url"]): tried.append(f"{c['model']} is asleep"); continue
        for _ in range(2):
            try:
                raw = _json_in(_chat(c, FILM_RULES + str(sentence)))
                if raw and len(raw.get("shots") or []) >= 4: return normalize_plan(raw, sentence, c["model"])
            except Exception as e: tried.append(f"{c['model']}: {type(e).__name__}")
    return fallback_plan(sentence, "; ".join(tried) or "no language model was reachable")
def _caption(m):
    return (f"Global Metadata\nBasic Attributes: bpm is {m['bpm']}. {m['style']}.\nGlobal Emotional Progression: {m['mood']}\nApplication Scenarios & Imagery: The score of a short film, under picture from start to finish.\nSonics & Production Profile: A clean, wide, cinematic mix with a steady pulse that is easy to cut to.\n"
            f"Vocal Details\nVocal Gender & Timbre: No vocals. Purely instrumental.\nVocal Style: No vocals.\nHarmony/Backing Vocals: None.\nVocal FX: None.\nArrangement\nInstrument Lifecycle Description (Primary/Secondary Layering):\nPrimary: {m['instruments']}.\nSecondary: Soft pads and quiet textures that widen as it builds.\nGroove & Foundation Progression: A clear, even {m['bpm']} BPM pulse from the first bars, with percussion joining as it grows.\nEmbellishments, Textures & Spatial FX: Risers and swells into each new section, a warm hall reverb.")
KLEIN_EDIT = "image_flux2_klein_image_edit_4b_distilled"; KLEIN_NOTE = "FLUX.2 Klein 4B, with the character frame as its reference"
def _key_step(sid, label, prompt, seed):
    return {"id": sid, "type": "template", "template": KLEIN_EDIT, "label": label, "model": KLEIN_NOTE, "peak_gib": 23, "seed": seed, "seed_node": "75:73", "seed_input": "noise_seed", "values": {"76|image": "@character"}, "swap": {"flux-2-klein-4b-fp8.safetensors": "flux-2-klein-4b.safetensors"}, "set": {"75:74": {"text": prompt}, "75:66": {"width": 1344, "height": 768}, "75:62": {"width": 1344, "height": 768}}, "prompt_note": prompt[:200]}
def film_specs(plan, seed=4242):
    from studio.goals import CAMERA_MOVES, SHOTS
    ch, world, look = plan["character"], plan["world"], plan["look"]; end = "No text, no logos."; steps = [{"id": "character", "type": "goal", "goal": "image", "label": "Character frame", "model": "FLUX.2 Klein 4B", "peak_gib": 23, "seed": seed, "options": {"aspect": "2:3", "mode": "quality"}, "prompt": f"Full body character design: {ch} Standing, facing the camera, the whole figure in frame, plain light grey studio background, soft even light. {end}"},
             _key_step("style", "Style frame", f"Wide establishing film still. The same character as in the reference picture, small in the frame, in this place: {world} {look}. {end}", seed + 1)]
    for i, s in enumerate(plan["shots"], 1):
        steps.append(_key_step(f"key{i}", f"Keyframe {i}", f"{SHOTS.get(s['shot'], '')} Film still. The same character as in the reference picture, same clothing and colours: {ch} {s['action']} The place: {world} {look}. {end}".strip(), seed + 1 + i))
        cam = CAMERA_MOVES.get(s["camera"], ""); steps.append({"id": f"shot{i}", "type": "goal", "goal": "h3_animate", "label": f"Shot {i}", "model": "MiniMax H3", "peak_gib": 46, "seed": seed + 10 + i, "image": f"@key{i}", "options": {"aspect": "16:9", "quality": "high", "seconds": 5, "speed": "fast"},
            "prompt": f"For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.\n\nintegrated_multimodal_description: [Shot 1] {look}. {ch} {s['action']} {cam} One continuous shot, no cuts.\n\noverall_soundscape: {s['sound']}\n\nnon_diegetic_music: N/A"})
    steps.append({"id": "score", "type": "goal", "goal": "music", "label": "Score", "model": "MiniMax Music 3", "peak_gib": 27, "seed": seed + 40, "options": {"seconds": 60}, "prompt": _caption(plan["music"]), "lyrics": "[intro]\n\n[instrumental]\n\n[solo]\n\n[instrumental]\n\n[outro]"})
    steps.append({"id": "cut", "type": "cpu", "op": "beat_cut", "label": "Cut on the beat", "final": True, "clips": [f"@shot{i}" for i in range(1, len(plan["shots"]) + 1)], "audio": "@score", "args": {"total_max": 32, "clip_audio_db": -12}})
    return steps

# ---------- run state
RUNS: dict = {}; QUEUE: "queue.Queue[str]" = queue.Queue(); _LOCK = threading.RLock(); _WORKER = {"t": None}; CURRENT = {"run": None}
def _save(run):
    with _LOCK:
        d = _root() / run["run"]; d.mkdir(parents=True, exist_ok=True); tmp = d / "run.json.part"; tmp.write_text(json.dumps({k: v for k, v in run.items() if not k.startswith("_")}, indent=1)); os.replace(tmp, d / "run.json")
def _pending(): return [r for r in RUNS.values() if r["status"] == "queued"]
def position(run): return 1 + sorted(_pending(), key=lambda r: r["created"]).index(run) if run["status"] == "queued" else 0
def _public(run):
    with _LOCK: out = {k: v for k, v in run.items() if not k.startswith("_")}; out["position"] = position(run) if run in RUNS.values() else 0; return out
def get_run(rid):
    if not re.fullmatch(r"[0-9a-f]{12}", rid or ""): return None
    if rid in RUNS: return RUNS[rid]
    p = _root() / rid / "run.json"
    if not p.is_file(): return None
    d = json.load(open(p))
    if d.get("status") in ("queued", "running"): d["status"] = "interrupted"; d["error"] = "The server restarted while this run was going. Finished steps are kept; run the recipe again for the rest."
    return d
def list_runs(rid=None, limit=20):
    rows = {}
    try:
        for p in sorted(_root().glob("*/run.json"), key=lambda x: x.stat().st_mtime, reverse=True)[:200]:
            try: d = get_run(p.parent.name)
            except Exception: continue
            if d and (rid is None or d.get("recipe") == rid): rows[d["run"]] = d
    except OSError: pass
    return sorted(rows.values(), key=lambda r: r.get("created", 0), reverse=True)[:limit]

# ---------- talking to the studio's own internals
class _Req:
    def __init__(self, b): self.b = b
    async def json(self): return self.b
class _File:
    def __init__(self, name, data, ctype): self.filename, self._d, self.content_type = name, data, ctype
    async def read(self): return self._d
def _detail(e): return str(getattr(e, "detail", "") or e)[:400]
def upload(path):
    S = _srv(); p = Path(path); ctype = {".png": "image/png", ".webp": "image/webp", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".mp4": "video/mp4", ".flac": "audio/flac", ".wav": "audio/wav", ".mp3": "audio/mpeg"}.get(p.suffix.lower(), "application/octet-stream")
    try: return asyncio.run(S.upload(_File(p.name, p.read_bytes(), ctype)))["name"]
    except Exception as e: raise StepError(f"could not hand {p.name} to the next step: {_detail(e)}") from None
def _localize(run, f):
    """A step's output as a local path: ComfyUI's output folder when it is shared with the studio, else fetched through /view (ComfyUI on another machine)."""
    S = _srv(); p = Path(S.OUTPUT) / f.get("subfolder", "") / f["filename"]
    if f.get("local") and Path(f["local"]).is_file(): return f["local"]
    if p.is_file(): return str(p)
    dst = _root() / run["run"] / f["filename"]
    if not dst.exists():
        q = urllib.parse.urlencode({"filename": f["filename"], "subfolder": f.get("subfolder", ""), "type": f.get("type", "output")})
        with urllib.request.urlopen(S.COMFY + "/view?" + q, timeout=300) as r: dst.write_bytes(r.read())
    return str(dst)
def _vram():
    d = (_srv().comfy("/system_stats", timeout=30).get("devices") or [{}])[0]; return d.get("vram_free", 0) / 2**30, d.get("vram_total", 0) / 2**30          # 30 s: ComfyUI answers slowly while it samples
def _used_gib():
    """Whole-card use: nvidia-smi when ComfyUI is on this machine (it matches the render windows' numbers), else ComfyUI's own count."""
    try:
        if re.search(r"//(127\.0\.0\.1|localhost)[:/]", _srv().COMFY + "/") and shutil.which("nvidia-smi"):
            r = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits", "-i", "0"], capture_output=True, text=True, timeout=5)
            return float(r.stdout.strip().splitlines()[0]) / 1024
    except Exception: pass
    try: f, t = _vram(); return t - f
    except Exception: return 0.0
def _unload():
    try: _srv().comfy("/free", {"unload_models": True, "free_memory": True}, timeout=15)
    except Exception: pass
def _check_cancel(run):
    if run.get("_cancel"): raise Cancelled()
def _vram_gate(run, st, peak):
    """The studio's VRAM rule: free memory must cover the step's measured peak + 4 GiB. A card smaller than that peak still runs, since ComfyUI offloads: then it asks for 90% of the card. It unloads ComfyUI first and otherwise waits, showing why, then gives up with the numbers."""
    for tries in range(4):
        try: free, total = _vram(); break
        except Exception as e:
            if tries == 3: raise StepError(f"ComfyUI is not reachable: {_detail(e)}") from None
            time.sleep(POLL); _check_cancel(run)
    need = min(peak + HEADROOM, total * 0.9) if total else peak + HEADROOM
    if free >= need: return
    _unload(); t0 = time.time()
    while True:
        time.sleep(POLL); _check_cancel(run)
        try: free, total = _vram()
        except Exception: continue
        if free >= need: st.pop("note", None); _save(run); return
        st["note"] = f"Waiting for GPU memory: {free:.0f} GiB free, this step needs {need:.0f}"; _save(run)
        if time.time() - t0 > VRAM_WAIT: raise StepError(f"Not enough free GPU memory: {free:.0f} GiB free after {VRAM_WAIT // 60} minutes, this step needs {need:.0f} GiB ({peak:.0f} peak + {HEADROOM:.0f} kept free). Close what else is using the card and run it again.")
def _wait_job(run, st, jid):
    S = _srv(); st["job"] = jid; t0 = time.time(); _save(run)
    while time.time() - t0 < STEP_LIMIT:
        time.sleep(POLL)
        if run.get("_cancel"):
            try: S.cancel(jid)
            except Exception: pass
            raise Cancelled()
        s = S.job(jid)
        if s.get("status") == "done": return s.get("files") or []
        if s.get("status") == "error": raise StepError(s.get("error") or "the render failed")
        if s.get("status") == "queued": st["note"] = f"In line in ComfyUI, position {s.get('position') or 1}"
        else: st.pop("note", None)
    raise StepError(f"gave up after {STEP_LIMIT // 60} minutes")
def _pick(ctx, ref, kind=None):
    """'@step' -> that step's output file (a dict with a local path): of the wanted kind when it has several."""
    sid = ref[1:]; files = ctx["out"].get(sid)
    if not files: raise StepError(f"step {sid} has no output to pass on")
    return next((f for f in files if not kind or f["kind"] == kind), None) or files[0]
def _input_name(run, ctx, ref, kind):
    if not (isinstance(ref, str) and ref.startswith("@")): return ref
    f = _pick(ctx, ref, kind)
    if "upload" not in f: f["upload"] = upload(f["local"])
    return f["upload"]
def goal_body(spec, values, seed_add=0):
    b = {"goal": spec["goal"], "prompt": _fill(spec.get("prompt", ""), values), "options": dict(spec.get("options") or {})}
    for k in ("lyrics", "target", "scene", "negative"):
        if k in spec: b[k] = _fill(spec[k], values)
    if "seed" in spec: b["seed"] = int(spec["seed"]) + seed_add
    return b
def _keep_graph(run, st, make):
    """The exact graph of a step, next to the run, so it is one click away even after ComfyUI forgets its history."""
    try: (_root() / run["run"] / f"{st['id']}.graph.json").write_text(json.dumps(make()))
    except Exception: pass
def _run_goal(run, st, spec, ctx):
    S = _srv(); b = goal_body(spec, ctx["values"], ctx["seed_add"])
    for k, kind in (("image", "image"), ("last_image", "image"), ("video", "video")):
        if spec.get(k): b[k] = _input_name(run, ctx, spec[k], kind)
    try: j = asyncio.run(S.generate(_Req(b)))
    except Exception as e: raise StepError(_detail(e)) from None
    st["seed"] = j.get("seed"); st["graph_hash"] = j.get("graph_hash"); b["seed"] = j.get("seed"); st["body"] = b; _keep_graph(run, st, lambda: S._graph(b["goal"], b, b.get("image"))[0]); return _wait_job(run, st, j["job"])
def template_graph(spec, values_in, oi, path):
    """A local ComfyUI template with this step's values. `set` writes node inputs the template does not promote; `swap` replaces a model file the template names when this box has another build of the same model, and only then."""
    from studio import apps as A
    g = A.build_graph(path, values_in, oi)
    for nid, kv in (spec.get("set") or {}).items():
        if nid not in g: raise StepError(f"template {spec['template']} has no node {nid}")
        g[nid]["inputs"].update(kv)
    swap = spec.get("swap") or {}
    if swap:
        known = {x for n in oi.values() for sec in ("required", "optional") for sp in ((n.get("input") or {}).get(sec) or {}).values() if isinstance(sp, list) and sp and isinstance(sp[0], list) for x in sp[0] if isinstance(x, str)}
        for n in g.values():
            for k, v in n["inputs"].items():
                if isinstance(v, str) and v in swap and v not in known: n["inputs"][k] = swap[v]
    return g
def _run_template(run, st, spec, ctx):
    from studio import apps as A, edits as E
    S = _srv(); path = E._path(spec["template"])
    if not path: raise StepError(f"the ComfyUI template {spec['template']} is not installed")
    vals = {}
    for k, v in (spec.get("values") or {}).items():
        kind = "video" if k.endswith("|file") else "image" if k.endswith("|image") else None
        vals[k] = _input_name(run, ctx, v, kind) if isinstance(v, str) and v.startswith("@") else (_fill(v, ctx["values"]) if isinstance(v, str) else v)
    spec2 = {**spec, "set": {nid: {k: (_fill(v, ctx["values"]) if isinstance(v, str) else v) for k, v in kv.items()} for nid, kv in (spec.get("set") or {}).items()}}
    if "seed_node" in spec and "seed" in spec: spec2["set"].setdefault(spec["seed_node"], {})[spec.get("seed_input", "seed")] = int(spec["seed"]) + ctx["seed_add"]
    oi = A.object_info()
    try: g = template_graph(spec2, vals, oi, path)
    except ValueError as e: raise StepError(str(e)) from None
    try: r = S.comfy("/prompt", {"prompt": g, "client_id": S.CLIENT_ID})
    except Exception as e:
        body = ""
        try: body = e.read().decode()[:300]
        except Exception: pass
        raise StepError(f"ComfyUI rejected the graph: {body or _detail(e)}") from None
    _keep_graph(run, st, lambda: g); jid = r["prompt_id"]; S.JOBS[jid] = {"goal": "template:" + spec["template"], "prompt": _fill(spec.get("prompt_note", spec["template"]), ctx["values"]), "started": time.time(), "options": {}}
    return _wait_job(run, st, jid)
def _cpu(run, st, spec, ctx):
    op = spec["op"]; d = _root() / run["run"]; d.mkdir(parents=True, exist_ok=True); out = d / f"{spec['id']}.{'png' if op == 'frame' else 'mp4'}"
    cl = lambda refs, kind="video": [_pick(ctx, r, kind)["local"] for r in refs]; a = spec.get("args") or {}
    if op == "frame": r = frame(_pick(ctx, spec["clip"], "video")["local"], out, a.get("which", "last"))
    elif op == "join": r = join(cl(spec["clips"]), out, float(a.get("crossfade", 0)), bool(a.get("keep_audio", True)))
    elif op == "beat_cut": r = beat_cut(cl(spec["clips"]), _pick(ctx, spec["audio"], "audio")["local"], out, a.get("total_max"), a.get("section", "energy"), float(a.get("head", 0.25)), a.get("clip_audio_db"))
    elif op == "cut_between": r = cut_between(cl(spec["clips"]), out, int(a.get("audio_from", 0)), a.get("pieces"))
    elif op == "loop": r = loop_seam(_pick(ctx, spec["clip"], "video")["local"], out, float(a.get("crossfade", 0.5)))
    elif op == "compare": r = compare(cl(spec["clips"]), out, a.get("labels"), a.get("audio_from"), a.get("height"), a.get("mode", "grid"))
    elif op == "mux": r = mux(_pick(ctx, spec["clip"], "video")["local"], _pick(ctx, spec["audio"], "audio")["local"], out)
    else: raise StepError(f"unknown step {op}")
    st["note"] = r.get("note", ""); st["facts"] = r.get("facts") or {}
    return [{"filename": out.name, "subfolder": "", "type": "recipe", "kind": r["kind"], "local": str(out), "url": f"/api/recipes/files/{run['run']}/{out.name}"}]
def _sampler(box, stop):
    while not stop.is_set(): box[0] = max(box[0], _used_gib()); stop.wait(2)
def _execute(run, rec):
    S = _srv(); ctx = {"values": run["values"], "seed_add": int(run.get("seed_add") or 0), "out": {}}; run["status"] = "running"; run["started"] = time.time(); CURRENT["run"] = run["run"]; _save(run); peak = 0.0
    specs = {s["id"]: s for s in (run.get("specs") or rec["steps"])}
    try:
        for st in run["steps"]:
            _check_cancel(run)
            if st["type"] == "plan":
                st["status"] = "running"; st["started"] = time.time(); _save(run); run["plan"] = plan_film(run["values"].get("sentence", "")); st.update(status="done", seconds=round(time.time() - st["started"], 1), note="Written by " + run["plan"]["writer"]); run["specs"] = film_specs(run["plan"], 4242 + int(run.get("seed_add") or 0)); specs = {s["id"]: s for s in run["specs"]}; run["steps"] += [_step_state(s) for s in run["specs"]]; _save(run); continue
            spec = specs[st["id"]]; kind = spec["type"]
            if st["id"] in (run.get("uploads") or {}):                                                       # the user brought their own picture or clip for this step
                name = run["uploads"][st["id"]]; f = {"filename": name, "subfolder": "", "type": "input", "kind": "video" if re.search(r"\.(mp4|webm|mov|mkv)$", name, re.I) else "audio" if re.search(r"\.(wav|mp3|flac)$", name, re.I) else "image", "upload": name, "url": "/api/view?" + urllib.parse.urlencode({"filename": name, "type": "input"})}
                f["local"] = _localize(run, f); ctx["out"][st["id"]] = [f]; st.update(status="skipped", note="Using your upload", files=[{k: f[k] for k in ("filename", "kind", "url")}]); _save(run); continue
            st["status"] = "running"; st["started"] = time.time(); _save(run); box = [0.0]; stop = threading.Event(); th = None
            try:
                if kind != "cpu":
                    _vram_gate(run, st, float(spec.get("peak_gib") or 8)); st["started"] = time.time(); _save(run)
                    th = threading.Thread(target=_sampler, args=(box, stop), daemon=True); th.start()
                    files = _run_goal(run, st, spec, ctx) if kind == "goal" else _run_template(run, st, spec, ctx)
                    for f in files: f["local"] = _localize(run, f)
                else: files = _cpu(run, st, spec, ctx)
            finally:
                stop.set()
                if th: th.join(timeout=3)
                if kind != "cpu": _unload(); time.sleep(POLL)
            ctx["out"][st["id"]] = files; st["files"] = [{k: f[k] for k in ("filename", "kind", "url") if k in f} for f in files]; st["status"] = "done"; st["seconds"] = round(time.time() - st["started"], 1)
            if kind != "cpu": st["peak_gib"] = round(box[0], 1); peak = max(peak, box[0])
            st.pop("note", None) if kind != "cpu" else None; _save(run)
        fin = next((s for s in reversed(run["steps"]) if s.get("final")), run["steps"][-1]); run["output"] = next((f for f in (fin.get("files") or []) if f["kind"] != "image"), (fin.get("files") or [None])[0]); run["status"] = "done"
    except Cancelled:
        run["status"] = "cancelled"; _mark(run, "cancelled")
    except StepError as e:
        run["status"] = "error"; run["error"] = str(e); _mark(run, "error", str(e))
    except Exception as e:
        run["status"] = "error"; run["error"] = f"{type(e).__name__}: {str(e)[:300]}"; _mark(run, "error", run["error"])
    run["finished"] = time.time(); run["seconds"] = round(run["finished"] - run["started"], 1); run["peak_vram_gib"] = round(peak, 1); CURRENT["run"] = None; _save(run)
def _step_state(s): return {"id": s["id"], "label": s.get("label", s["id"]), "type": s["type"], "status": "pending", "final": bool(s.get("final")), "model": s.get("model", "")}
def _mark(run, status, msg=""):
    for st in run["steps"]:
        if st["status"] == "running":
            st["status"] = status; st["seconds"] = round(time.time() - st.get("started", time.time()), 1)
            if msg: st["error"] = msg
def _worker():
    while True:
        rid = QUEUE.get(); run = RUNS.get(rid)
        if not run or run["status"] != "queued": continue
        if run.get("_cancel"): run["status"] = "cancelled"; _save(run); continue
        rec = find(run["recipe"])
        try: _execute(run, rec)
        except Exception as e: run["status"] = "error"; run["error"] = f"{type(e).__name__}: {str(e)[:300]}"; _save(run)
def _ensure_worker():
    with _LOCK:
        if not _WORKER["t"] or not _WORKER["t"].is_alive(): _WORKER["t"] = threading.Thread(target=_worker, daemon=True, name="recipes"); _WORKER["t"].start()

def library_rows(limit=40):
    """Finished recipe films for the Library, next to what ComfyUI's history lists: each opens with its steps, and each step's graph, one click away."""
    rows = []
    for r in list_runs(None, limit):
        o = r.get("output")
        if r.get("status") == "done" and o: rows.append({"job": r["run"], "files": [{"filename": o.get("filename"), "subfolder": "", "type": "recipe", "url": o.get("url"), "kind": o.get("kind", "video")}], "goal": "recipe", "prompt": (r.get("values") or {}).get("sentence") or r.get("title"), "options": {}, "recipe": {"id": r.get("recipe"), "run": r["run"], "title": r.get("title")}})
    return rows

# ---------- what the page shows
def find(rid):
    return next((r for r in load()["recipes"] if r["id"] == rid), None)
def _step_view(s, d):
    kind = s["type"]; m = d.get("measured", {}); key = s.get("goal") if kind == "goal" else s.get("template") if kind == "template" else None; me = m.get(key or "", {}); ops = d.get("cpu_ops", {})
    out = {"id": s["id"], "label": s.get("label", s["id"]), "type": kind, "goal": s.get("goal"), "template": s.get("template"), "op": s.get("op"), "model": s.get("model") or me.get("model") or ("ffmpeg, on the CPU" if kind == "cpu" else ""), "seconds": me.get("seconds"), "peak_gib": s.get("peak_gib") or me.get("peak_gib") or None, "swappable": bool(s.get("swappable")), "accepts": s.get("accepts"), "final": bool(s.get("final")), "what": s.get("what") or ops.get(s.get("op") or "", "")}
    return out
def view(rec, d=None):
    d = d or load(); steps = [_step_view(s, d) for s in rec["steps"]]; t = rec.get("tested") or None; exp_s = sum(int(s["seconds"] or 0) for s in steps); gpu = [s["peak_gib"] for s in steps if s["peak_gib"]]
    return {**{k: rec.get(k) for k in ("id", "title", "pitch", "why", "tags", "fields", "models", "licence_summary", "tips", "variations")}, "steps": steps, "status": "tested" if t else "untested", "tested": t, "expected": {"seconds": exp_s, "peak_gib": max(gpu) if gpu else 0, "basis": "sum of each step's measured time on this box, with a cold start per step" if exp_s else "not measured"}}
def validate(d=None):
    """Problems in recipes.json. A test keeps it clean; the page never has to guess."""
    from studio.goals import GOALS
    d = d or load(); probs = []; seen = set()
    for r in d["recipes"]:
        rid = r.get("id", "?"); done = set()
        if rid in seen: probs.append(f"{rid}: duplicate id")
        seen.add(rid)
        for k in ("title", "pitch", "why", "steps", "models", "tags"):
            if not r.get(k): probs.append(f"{rid}: no {k}")
        keys = {f["key"] for f in r.get("fields", [])}
        for s in r.get("steps", []):
            sid = s.get("id")
            if not sid or sid in done: probs.append(f"{rid}: bad step id {sid}")
            ty = s.get("type")
            if ty == "goal":
                g = GOALS.get(s.get("goal"))
                if not g: probs.append(f"{rid}/{sid}: unknown goal {s.get('goal')}"); continue
                for k, v in (s.get("options") or {}).items():
                    if k not in g["options"] or v not in g["options"][k]: probs.append(f"{rid}/{sid}: option {k}={v} is not offered by {s['goal']}")
                if g["needs_image"] and not s.get("image"): probs.append(f"{rid}/{sid}: {s['goal']} needs an image")
                if g["needs_video"] and not s.get("video"): probs.append(f"{rid}/{sid}: {s['goal']} needs a video")
                if g["needs_last_image"] and not s.get("last_image"): probs.append(f"{rid}/{sid}: {s['goal']} needs a last image")
                if not g["prompt_optional"] and not s.get("prompt"): probs.append(f"{rid}/{sid}: {s['goal']} needs a prompt")
                if not s.get("peak_gib"): probs.append(f"{rid}/{sid}: no peak_gib for the VRAM gate")
            elif ty == "template":
                if not s.get("template"): probs.append(f"{rid}/{sid}: no template")
                if not s.get("peak_gib"): probs.append(f"{rid}/{sid}: no peak_gib for the VRAM gate")
            elif ty == "cpu":
                if s.get("op") not in ("frame", "join", "beat_cut", "cut_between", "loop", "compare", "mux"): probs.append(f"{rid}/{sid}: unknown op {s.get('op')}")
            elif ty != "plan": probs.append(f"{rid}/{sid}: unknown type {ty}")
            refs = [v for k, v in s.items() if k in ("image", "last_image", "video", "clip", "audio") and isinstance(v, str)] + list(s.get("clips") or []) + [v for v in (s.get("values") or {}).values() if isinstance(v, str) and v.startswith("@")]
            for x in refs:
                if not str(x).startswith("@") or str(x)[1:] not in done: probs.append(f"{rid}/{sid}: reference {x} is not an earlier step")
            for k in ("prompt", "lyrics", "target", "scene"):
                for m in re.findall(r"\{([a-z_][a-z0-9_]*)\}", str(s.get(k, ""))):
                    if m not in keys: probs.append(f"{rid}/{sid}: {k} uses {{{m}}} but the recipe has no such field")
            done.add(sid)
        for m in r.get("models", []):
            if not m.get("name") or not m.get("licence"): probs.append(f"{rid}: a model without a name or licence")
        t = r.get("tested")
        if t:
            for k in ("output", "media", "poster", "seconds", "peak_vram_gib", "rendered", "steps"):
                if k not in t: probs.append(f"{rid}: tested without {k}")
            for k in ("media", "poster"):
                if t.get(k) and not (HERE / "web" / t[k]).is_file(): probs.append(f"{rid}: tested {k} {t[k]} is not in the web folder")
    return probs

# ---------- API
router = APIRouter()
class RunReq(BaseModel): values: dict = {}; uploads: dict = {}; seed_add: int = 0; plan: dict | None = None
class PlanReq(BaseModel): sentence: str
@router.get("/api/recipes")
def recipes_list():
    d = load(); rows = [view(r, d) for r in d["recipes"]]; return {"recipes": rows, "measured": d.get("measured", {}), "tested": sum(1 for r in rows if r["status"] == "tested"), "untested": sum(1 for r in rows if r["status"] != "tested"), "busy": CURRENT["run"], "queued": len(_pending())}
@router.get("/api/recipes/files/{rid}/{name}")
def recipe_file(rid: str, name: str):
    if not re.fullmatch(r"[0-9a-f]{12}", rid) or not re.fullmatch(r"[A-Za-z0-9_.-]+", name) or name.startswith("."): raise HTTPException(400, "bad path")
    p = _root() / rid / name
    if not p.is_file() or name == "run.json": raise HTTPException(404, "no such file")
    return FileResponse(p)
@router.get("/api/recipes/{rid}")
def recipe_get(rid: str):
    r = find(rid)
    if not r: raise HTTPException(404, "no such recipe")
    return {**view(r), "raw_steps": [{k: v for k, v in s.items() if k in ("id", "label", "goal", "template", "prompt", "lyrics", "options", "op", "args", "image", "last_image", "video", "clip", "clips", "audio", "target", "scene")} for s in r["steps"]]}
@router.post("/api/recipes/{rid}/plan")
def recipe_plan(rid: str, b: PlanReq):
    rec = find(rid)
    if not rec or rec.get("dynamic") != "film": raise HTTPException(404, "this recipe has no shot list")
    if not b.sentence.strip(): raise HTTPException(400, "write the sentence first")
    sfw.check(b.sentence)
    return plan_film(b.sentence[:400])
@router.post("/api/recipes/{rid}/run")
def recipe_run(rid: str, b: RunReq):
    rec = find(rid)
    if not rec: raise HTTPException(404, "no such recipe")
    for name in b.uploads.values():
        if not isinstance(name, str) or os.path.basename(name) != name or not re.search(r"\.(png|jpe?g|webp|mp4|webm|mov|mkv|wav|mp3|flac)$", name, re.I): raise HTTPException(400, "uploads must be names returned by /api/upload")
    bad = [k for k in b.uploads if k not in {s["id"] for s in rec["steps"] if s.get("swappable")}]
    if bad: raise HTTPException(400, f"step {bad[0]} does not take an upload")
    vals = {**field_defaults(rec), **{k: str(v)[:1500] for k, v in b.values.items() if k in field_defaults(rec)}}; rid2 = uuid.uuid4().hex[:12]
    sfw.check(*vals.values())
    run = {"run": rid2, "recipe": rid, "title": rec["title"], "status": "queued", "created": time.time(), "values": vals, "uploads": b.uploads, "seed_add": b.seed_add, "steps": [_step_state(s) for s in rec["steps"]]}
    if rec.get("dynamic") == "film":
        if b.plan: run["plan"] = normalize_plan(b.plan, vals.get("sentence", ""), b.plan.get("writer") or "edited by you"); run["specs"] = film_specs(run["plan"], 4242 + b.seed_add); run["steps"] = [_step_state(s) for s in run["specs"]]
        else: run["steps"] = [{"id": "plan", "label": "Write the shot list", "type": "plan", "status": "pending", "final": False, "model": "local language model"}]
    with _LOCK: RUNS[rid2] = run
    _save(run); _ensure_worker(); QUEUE.put(rid2); return {"run": rid2, "position": position(run), "status": "queued"}
@router.get("/api/recipes/{rid}/runs")
def recipe_runs(rid: str, limit: int = 8):
    if not find(rid): raise HTTPException(404, "no such recipe")
    return {"runs": [{k: r.get(k) for k in ("run", "status", "created", "seconds", "peak_vram_gib", "output", "error", "values")} for r in list_runs(rid, min(limit, 40))]}
@router.get("/api/recipes/{rid}/runs/{run}")
def recipe_run_get(rid: str, run: str):
    r = get_run(run)
    if not r or r.get("recipe") != rid: raise HTTPException(404, "no such run")
    return _public(r) if run in RUNS else {**r, "position": 0}
@router.get("/api/recipes/{rid}/runs/{run}/graph/{step}")
def recipe_run_graph(rid: str, run: str, step: str):
    r = get_run(run)
    if not r or r.get("recipe") != rid or not re.fullmatch(r"[A-Za-z0-9_-]+", step): raise HTTPException(404, "no such run")
    p = _root() / run / f"{step}.graph.json"
    if not p.is_file(): raise HTTPException(404, "this step has no graph")
    return {"graph": json.load(open(p))}
@router.post("/api/recipes/{rid}/runs/{run}/cancel")
def recipe_run_cancel(rid: str, run: str):
    r = RUNS.get(run)
    if not r or r.get("recipe") != rid: raise HTTPException(404, "no such run")
    r["_cancel"] = True
    if r["status"] == "queued": r["status"] = "cancelled"; _save(r)
    return {"ok": True, "status": r["status"]}
