import os
import sys
import tempfile
import subprocess
import json
import shutil
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline_render import render_edl, edl_problems


def _make_clip(ffmpeg, path, duration=1.0, w=160, h=90, fps=25):
    cmd = [
        ffmpeg, '-y',
        '-f', 'lavfi', '-i', f'testsrc2=size={w}x{h}:rate={fps}:duration={duration}',
        '-f', 'lavfi', '-i', f'sine=frequency=440:duration={duration}',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac',
        '-shortest',
        str(path)
    ]
    subprocess.run(cmd, capture_output=True, check=True)


def _make_audio_clip(ffmpeg, path, duration=1.0):
    cmd = [
        ffmpeg, '-y',
        '-f', 'lavfi', '-i', f'sine=frequency=880:duration={duration}',
        '-c:a', 'aac',
        str(path)
    ]
    subprocess.run(cmd, capture_output=True, check=True)


def _probe(ffmpeg, path):
    ffprobe = ffmpeg.replace('ffmpeg', 'ffprobe')
    result = subprocess.run(
        [ffprobe, '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', str(path)],
        capture_output=True,
        text=True,
        check=True
    )
    return json.loads(result.stdout)


def test_rejections():
    with tempfile.TemporaryDirectory() as tmp:
        root = os.path.join(tmp, 'root')
        os.makedirs(root)
        out = os.path.join(tmp, 'out.mp4')

        # Absolute path
        edl = {
            'fps': 25, 'duration': 2,
            'tracks': [{'kind': 'video', 'clips': [{'src': '/etc/passwd', 'start': 0, 'dur': 1, 'in': 0}]}]
        }
        probs = edl_problems(edl, root)
        assert any('absolute' in p for p in probs), f"Expected absolute path rejection, got {probs}"

        # Path traversal
        edl2 = {
            'fps': 25, 'duration': 2,
            'tracks': [{'kind': 'video', 'clips': [{'src': '../secret.mp4', 'start': 0, 'dur': 1, 'in': 0}]}]
        }
        probs2 = edl_problems(edl2, root)
        assert any('traversal' in p or 'escapes' in p for p in probs2), f"Expected traversal rejection, got {probs2}"

        # Missing file
        edl3 = {
            'fps': 25, 'duration': 2,
            'tracks': [{'kind': 'video', 'clips': [{'src': 'nonexistent.mp4', 'start': 0, 'dur': 1, 'in': 0}]}]
        }
        probs3 = edl_problems(edl3, root)
        assert any('not found' in p for p in probs3), f"Expected missing file rejection, got {probs3}"

        # Too many clips
        clips = [{'src': 'x.mp4', 'start': 0, 'dur': 0.1, 'in': 0} for _ in range(41)]
        edl4 = {
            'fps': 25, 'duration': 2,
            'tracks': [{'kind': 'video', 'clips': clips}]
        }
        probs4 = edl_problems(edl4, root)
        assert any('too many' in p for p in probs4), f"Expected too many clips rejection, got {probs4}"

        # Render should fail without calling ffmpeg
        result = render_edl(edl, out, root)
        assert not result['ok']
        assert result['problems']


def test_render():
    ffmpeg = 'ffmpeg'
    with tempfile.TemporaryDirectory() as tmp:
        root = os.path.join(tmp, 'root')
        os.makedirs(root)
        out = os.path.join(tmp, 'out.mp4')

        # Create two video clips with audio
        clip1 = os.path.join(root, 'clip1.mp4')
        clip2 = os.path.join(root, 'clip2.mp4')
        _make_clip(ffmpeg, clip1, duration=1.0)
        _make_clip(ffmpeg, clip2, duration=1.0)

        # Create an audio-only clip
        audio_clip = os.path.join(root, 'audio.mp4')
        _make_audio_clip(ffmpeg, audio_clip, duration=1.0)

        # Build EDL: clip1 at 0-1s, clip2 at 1-2s, audio at 0-1s
        edl = {
            'fps': 25,
            'duration': 2,
            'tracks': [
                {
                    'kind': 'video',
                    'clips': [
                        {'src': 'clip1.mp4', 'start': 0, 'dur': 1, 'in': 0},
                        {'src': 'clip2.mp4', 'start': 1, 'dur': 1, 'in': 0}
                    ]
                },
                {
                    'kind': 'audio',
                    'clips': [
                        {'src': 'audio.mp4', 'start': 0, 'dur': 1, 'in': 0}
                    ]
                }
            ]
        }

        result = render_edl(edl, out, root)
        assert result['ok'], f"Render failed: {result['problems']}"
        assert os.path.exists(out), "Output file not created"

        # Probe the output
        info = _probe(ffmpeg, out)
        fmt = info.get('format', {})
        streams = info.get('streams', [])

        # Check duration
        dur = float(fmt.get('duration', 0))
        assert abs(dur - 2.0) < 0.4, f"Duration {dur} not within 0.4s of 2.0"

        # Check video stream
        video_streams = [s for s in streams if s.get('codec_type') == 'video']
        assert len(video_streams) == 1, f"Expected 1 video stream, got {len(video_streams)}"
        vs = video_streams[0]
        assert vs.get('width') == 960, f"Expected width 960, got {vs.get('width')}"
        assert vs.get('height') == 544, f"Expected height 544, got {vs.get('height')}"

        # Check audio stream
        audio_streams = [s for s in streams if s.get('codec_type') == 'audio']
        assert len(audio_streams) == 1, f"Expected 1 audio stream, got {len(audio_streams)}"


def main():
    test_rejections()
    test_render()
    print('ok')


if __name__ == '__main__':
    main()
