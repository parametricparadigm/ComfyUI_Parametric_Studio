#!/usr/bin/env python3
"""Package real studio renders for the Create page: transcode to small web files in studio/web/showcase/ and write showcase.json with the prompt, goal and measured time/VRAM of each.
Usage: build_showcase.py <renders.json> [<renders.json> ...] [--skip name,name]. Later files win on name clashes."""
import json, os, subprocess, sys
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "studio", "web", "showcase"); os.makedirs(OUT, exist_ok=True)
def run(*a): subprocess.run(a, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
def probe(p):
    o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height", "-of", "csv=p=0", p], capture_output=True, text=True).stdout.strip().split(",")
    return int(o[0]), int(o[1])
args = [a for a in sys.argv[1:] if not a.startswith("--")]; skip = set()
if "--skip" in sys.argv: i = sys.argv.index("--skip"); skip = set(sys.argv[i + 1].split(",")); args.remove(sys.argv[i + 1])
items = {}
for rj in args:
    for name, r in json.load(open(os.path.expanduser(rj))).items():
        if r.get("status") != "ok" or name in skip: continue
        f = next((x for x in r["files"] if x["kind"] in ("video", "image", "audio")), None)
        if not f or not os.path.exists(f["file"]): continue
        row = {"id": name, "goal": r["goal"], "kind": f["kind"], "prompt": r["prompt"], "options": r.get("options", {}), "seconds": r.get("seconds"), "peak_vram_gib": r.get("peak_vram_gib")}
        if f["kind"] == "video":
            dst = f"{name}.mp4"; run("ffmpeg", "-y", "-i", f["file"], "-vf", "scale='min(960,iw)':-2", "-c:v", "libx264", "-crf", "24", "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", f"{OUT}/{dst}")
            run("ffmpeg", "-y", "-ss", "1", "-i", f["file"], "-frames:v", "1", "-vf", "scale='min(960,iw)':-2", "-q:v", "78", f"{OUT}/{name}.webp"); row.update(src=f"showcase/{dst}", poster=f"showcase/{name}.webp")
        elif f["kind"] == "image":
            run("ffmpeg", "-y", "-i", f["file"], "-vf", "scale='min(1280,iw)':-2", "-q:v", "82", f"{OUT}/{name}.webp"); row.update(src=f"showcase/{name}.webp", poster=f"showcase/{name}.webp")
        else:
            run("ffmpeg", "-y", "-i", f["file"], "-c:a", "aac", "-b:a", "128k", f"{OUT}/{name}.m4a"); row.update(src=f"showcase/{name}.m4a", poster=None, w=1, h=1); items[name] = row; continue
        row["w"], row["h"] = probe(f"{OUT}/{name}.webp"); items[name] = row
json.dump(list(items.values()), open(f"{OUT}/showcase.json", "w"), indent=0)
print(len(items), "items,", sum(os.path.getsize(f"{OUT}/{x}") for x in os.listdir(OUT)) >> 20, "MB")
