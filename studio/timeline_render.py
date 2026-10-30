import os
import subprocess
import json
from pathlib import Path


def _safe_resolve(root, rel):
    if not rel:
        return None, "empty path"
    if os.path.isabs(rel):
        return None, "absolute path"
    parts = Path(rel).parts
    if '..' in parts:
        return None, "path traversal"
    root_path = Path(root).resolve()
    target = (root_path / rel).resolve()
    try:
        target.relative_to(root_path)
    except ValueError:
        return None, "path escapes root"
    return target, None


def edl_problems(edl, root):
    problems = []
    if not isinstance(edl, dict):
        return ["EDL must be a dict"]

    fps = edl.get('fps')
    duration = edl.get('duration')
    tracks = edl.get('tracks', [])

    if not isinstance(fps, (int, float)) or fps <= 0:
        problems.append("invalid fps")
    if not isinstance(duration, (int, float)) or duration <= 0:
        problems.append("invalid duration")
    if duration > 600:
        problems.append("duration exceeds 600s")

    if not isinstance(tracks, list):
        problems.append("tracks must be a list")
        return problems

    total_clips = 0
    for i, track in enumerate(tracks):
        if not isinstance(track, dict):
            problems.append(f"track {i} invalid")
            continue
        kind = track.get('kind')
        if kind not in ('video', 'audio'):
            problems.append(f"track {i} invalid kind")
            continue
        clips = track.get('clips', [])
        if not isinstance(clips, list):
            problems.append(f"track {i} clips invalid")
            continue

        for j, clip in enumerate(clips):
            total_clips += 1
            if not isinstance(clip, dict):
                problems.append(f"track {i} clip {j} invalid")
                continue

            src = clip.get('src')
            if not src:
                problems.append(f"track {i} clip {j} missing src")
                continue

            target, err = _safe_resolve(root, src)
            if err:
                problems.append(f"track {i} clip {j}: {err}")
                continue

            if not target.exists():
                problems.append(f"track {i} clip {j}: file not found")
                continue

            if target.is_symlink():
                real_target = target.resolve()
                root_path = Path(root).resolve()
                try:
                    real_target.relative_to(root_path)
                except ValueError:
                    problems.append(f"track {i} clip {j}: symlink escapes root")

    if total_clips > 40:
        problems.append("too many clips")

    return problems


def _has_audio(ffprobe, path):
    try:
        result = subprocess.run(
            [ffprobe, '-v', 'quiet', '-print_format', 'json', '-show_streams', str(path)],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            return False
        data = json.loads(result.stdout)
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'audio':
                return True
        return False
    except Exception:
        return False


def render_edl(edl, out_path, root, size=(960, 544), ffmpeg='ffmpeg', timeout=600):
    problems = edl_problems(edl, root)
    if problems:
        return {
            'ok': False,
            'seconds': 0,
            'out_path': out_path,
            'problems': problems,
            'ffmpeg_stderr_tail': ''
        }

    fps = edl['fps']
    duration = edl['duration']
    tracks = edl['tracks']
    w, h = size
    ffprobe = ffmpeg.replace('ffmpeg', 'ffprobe')

    input_files = []
    video_clips = []
    audio_clips = []
    input_idx = 0

    for track in tracks:
        kind = track['kind']
        clips = track.get('clips', [])
        for clip in clips:
            src = clip['src']
            start = clip.get('start', 0)
            dur = clip.get('dur', 0)
            in_point = clip.get('in', 0)
            target, _ = _safe_resolve(root, src)
            if target is None:
                continue
            input_files.append(str(target))
            if kind == 'video':
                video_clips.append((input_idx, start, dur, in_point, target))
            else:
                audio_clips.append((input_idx, start, dur, in_point, target))
            input_idx += 1

    # Check which video clips have audio
    video_audio_clips = []
    for idx, start, dur, in_point, target in video_clips:
        if _has_audio(ffprobe, target):
            video_audio_clips.append((idx, start, dur, in_point, target))

    # All audio sources: audio track clips + video clips with audio
    all_audio = audio_clips + video_audio_clips

    # Build filter_complex
    filter_parts = []
    filter_parts.append(f"color=c=black:s={w}x{h}:r={fps}:d={duration}[base]")

    # Process video clips
    overlay_src = "base"
    for i, (idx, start, dur, in_point, target) in enumerate(video_clips):
        v_label = f"v{i}"
        filter_parts.append(
            f"[{idx}:v]trim=start={in_point}:duration={dur},"
            f"setpts=PTS-STARTPTS+{start}/TB,"
            f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2[{v_label}]"
        )
        next_label = f"ov{i}"
        filter_parts.append(f"[{overlay_src}][{v_label}]overlay=eof_action=pass[{next_label}]")
        overlay_src = next_label

    final_video_label = overlay_src

    # Process audio clips
    audio_labels = []
    for i, (idx, start, dur, in_point, target) in enumerate(all_audio):
        a_label = f"a{i}"
        delay_ms = int(start * 1000)
        filter_parts.append(
            f"[{idx}:a]atrim=start={in_point}:duration={dur},"
            f"asetpts=PTS-STARTPTS,"
            f"adelay={delay_ms}|{delay_ms}[{a_label}]"
        )
        audio_labels.append(a_label)

    has_audio = len(audio_labels) > 0
    if has_audio:
        if len(audio_labels) == 1:
            final_audio_label = audio_labels[0]
        else:
            mix_inputs = "".join(f"[{l}]" for l in audio_labels)
            filter_parts.append(f"{mix_inputs}amix=inputs={len(audio_labels)}:normalize=0[aout]")
            final_audio_label = "aout"

    filter_complex = ";".join(filter_parts)

    # Build ffmpeg command
    cmd = [ffmpeg, '-y']
    for f in input_files:
        cmd.extend(['-i', f])

    cmd.extend(['-filter_complex', filter_complex])
    cmd.extend(['-map', f'[{final_video_label}]'])
    if has_audio:
        cmd.extend(['-map', f'[{final_audio_label}]'])

    cmd.extend([
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-c:a', 'aac',
        '-movflags', '+faststart',
        '-f', 'mp4',
        out_path + '.part'
    ])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode != 0:
            stderr_tail = result.stderr[-2000:] if result.stderr else ''
            return {
                'ok': False,
                'seconds': 0,
                'out_path': out_path,
                'problems': ['ffmpeg failed'],
                'ffmpeg_stderr_tail': stderr_tail
            }

        os.rename(out_path + '.part', out_path)
        return {
            'ok': True,
            'seconds': duration,
            'out_path': out_path,
            'problems': [],
            'ffmpeg_stderr_tail': ''
        }
    except subprocess.TimeoutExpired:
        return {
            'ok': False,
            'seconds': 0,
            'out_path': out_path,
            'problems': ['timeout'],
            'ffmpeg_stderr_tail': ''
        }
    except Exception as e:
        return {
            'ok': False,
            'seconds': 0,
            'out_path': out_path,
            'problems': [str(e)],
            'ffmpeg_stderr_tail': ''
        }
