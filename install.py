#!/usr/bin/env python3
"""Box-aware installer for Parametric Studio. Standard library only; Python 3.10 or newer.

It looks at this machine, decides which models fit, prints the plan, and only after a yes creates a
virtual environment, clones ComfyUI, installs the Python packages, downloads the chosen model files
(resumable, SHA-256 checked) and writes a launcher. --dry-run prints every step and does nothing.

Status: tested with simulated hardware and with --dry-run. Not yet run end to end on a real Windows,
macOS or AMD machine. Run from a checkout of the repository.
"""
import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
from studio.boxcheck import describe, detect, plan  # noqa: E402  (standard library only)

EXIT_OK, EXIT_CANCELLED, EXIT_NOTHING, EXIT_FAILED = 0, 2, 3, 4
STUDIO_PACKAGES = ["fastapi", "uvicorn", "python-multipart", "pydantic", "numpy", "pillow"]

# Peak VRAM in GiB per goal: the highest figure from the studio's showcase renders on one 96 GB NVIDIA card,
# at small sizes and short lengths. Treat them as estimates on any other card.
PEAK_VRAM_GIB = {"image": 22.6, "anime": 13.2, "flux3": 24.1, "video": 34.7, "animate": 34.7,
                 "video_ltx": 44.3, "animate_ltx": 44.6, "h3_video": 45.4, "h3_animate": 46.8, "music": 26.8}
# Only NVIDIA has been tried. The other backends are listed where ComfyUI normally supports the model type.
BACKENDS = {"image": ["cuda", "rocm", "mps"], "anime": ["cuda", "rocm", "mps"], "video": ["cuda", "rocm", "mps"],
            "animate": ["cuda", "rocm", "mps"], "music": ["cuda", "rocm", "mps"], "flux3": ["cuda"],
            "video_ltx": ["cuda"], "animate_ltx": ["cuda"], "h3_video": ["cuda"], "h3_animate": ["cuda"]}
# The H3 text encoder is NVFP4; boxcheck reports that capability only on compute capability 10.0 and up.
NEEDS = {"h3_video": ["nvfp4"], "h3_animate": ["nvfp4"]}
# Custom node packs the shipped graphs need beyond ComfyUI core: LTXFloatToInt comes from this pack.
GOAL_PACKS = {"video_ltx": ["https://github.com/Lightricks/ComfyUI-LTXVideo.git"],
              "animate_ltx": ["https://github.com/Lightricks/ComfyUI-LTXVideo.git"]}



# Flagship apps. recast, vfx_ltx and director were measured on the author's box; reshoot, director_keyframes, orbit360 and reshoot_wan use the nearest measured H3 or Wan figure.
PEAK_VRAM_GIB.update({"product": 24.1, "recast": 36.3, "vfx_ltx": 44.8, "director": 45.6, "reshoot": 46.8, "director_keyframes": 46.8, "orbit360": 46.8, "reshoot_wan": 34.7})
BACKENDS["product"] = BACKENDS["flux3"]
BACKENDS.update({g: ["cuda"] for g in ("recast", "vfx_ltx", "director", "reshoot", "director_keyframes", "orbit360", "reshoot_wan")})
NEEDS.update({g: ["nvfp4"] for g in ("recast", "director", "reshoot", "director_keyframes", "orbit360")})
GOAL_PACKS.update({"vfx_ltx": ["https://github.com/Lightricks/ComfyUI-LTXVideo.git"], "recast": ["https://github.com/kijai/ComfyUI-KJNodes.git"]})
def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_venv_python_path(base_dir):
    base_dir = Path(base_dir)
    if platform.system() == "Windows":
        return base_dir / "venv" / "Scripts" / "python.exe"
    return base_dir / "venv" / "bin" / "python"


def to_plan_manifest(goal_manifest):
    """studio/models_manifest.json lists files per goal; boxcheck.plan wants models with variants."""
    models = []
    for goal, entry in goal_manifest["goals"].items():
        peak = PEAK_VRAM_GIB.get(goal, 0.0)
        models.append({"id": goal, "goal": goal, "note": entry.get("note", ""), "variants": [{
            "id": "default", "label": entry.get("note", goal), "quality": 1, "files": entry["files"],
            "peak_vram_gb": peak, "vram_basis": "estimate", "offload_ok": True, "min_ram_gb": max(16.0, peak),
            "needs": NEEDS.get(goal, []), "backends": BACKENDS.get(goal, ["cuda"])}]})
    return {"version": 1, "models": models}


def selected_files(plan_result, plan_manifest, include_gated=False):
    """-> (files to fetch, [(goal, why skipped)]). One file is listed once even when two goals share it."""
    variants = {m["goal"]: m["variants"][0] for m in plan_manifest["models"]}
    files, seen, skipped = [], set(), []
    for item in plan_result["items"]:
        goal = item["goal"]
        if item["mode"] not in ("gpu", "offload"):
            skipped.append((goal, item.get("reason") or "does not fit this machine"))
            continue
        goal_files = variants[goal]["files"]
        if any(f.get("gated") for f in goal_files) and not include_gated:
            skipped.append((goal, "gated download: accept the licence on Hugging Face, set HF_TOKEN, add --include-gated"))
            continue
        for f in goal_files:
            key = (f["repo"], f["path"])
            if key not in seen:
                seen.add(key)
                files.append(f)
    return files, skipped


def installed_goals(plan_result, skipped):
    gone = {g for g, _ in skipped}
    return [i["goal"] for i in plan_result["items"] if i["goal"] not in gone]


def build_commands(plan_result, plan_manifest, channels, channel, base_dir, backend, include_gated=False, models=True):
    """Pure: returns the steps as argument lists. Pseudo commands 'download' and 'link' run inside this script."""
    base_dir = Path(base_dir)
    python = str(get_venv_python_path(base_dir))
    comfy_dir = base_dir / "ComfyUI"
    cfg = channels[channel]
    clone = ["git", "clone", "--depth", "1", "--branch", cfg["comfyui"]["ref"], cfg["comfyui"]["repo"], str(comfy_dir)]
    cmds = [[sys.executable, "-m", "venv", str(base_dir / "venv")],
            [python, "-m", "pip", "install", "--upgrade", "pip"]]
    torch_args = cfg.get("torch", {}).get(backend, [])
    if torch_args:
        cmds.append([python, "-m", "pip", "install", *torch_args])
    cmds += [clone,
             [python, "-m", "pip", "install", "-r", str(comfy_dir / "requirements.txt")],
             [python, "-m", "pip", "install", *STUDIO_PACKAGES],
             ["link", str(REPO), str(comfy_dir / "custom_nodes" / "comfyui_parametric_studio")]]
    files, skipped = selected_files(plan_result, plan_manifest, include_gated)
    packs = []
    for goal in installed_goals(plan_result, skipped):
        packs += [p for p in GOAL_PACKS.get(goal, []) if p not in packs]
    for url in packs:
        dest = comfy_dir / "custom_nodes" / url.rsplit("/", 1)[1].removesuffix(".git")
        cmds.append(["git", "clone", "--depth", "1", url, str(dest)])
        cmds.append([python, "-m", "pip", "install", "-r", str(dest / "requirements.txt")])
    if models:
        for f in files:
            url = f"https://huggingface.co/{f['repo']}/resolve/main/{urllib.parse.quote(f['path'])}"
            cmds.append(["download", url, str(comfy_dir / "models" / f["dest"]), f["sha256"]])
    return cmds


class _DropTokenOnRedirect(urllib.request.HTTPRedirectHandler):
    """Hugging Face redirects large files to a CDN; the token stays on huggingface.co."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None and not (urllib.parse.urlparse(newurl).hostname or "").endswith("huggingface.co"):
            new.remove_header("Authorization")
        return new


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download_file(url, dest_path, sha256_expected, opener=None):
    """Resume with an HTTP Range request, verify SHA-256, keep nothing that fails the check."""
    opener = opener or urllib.request.build_opener(_DropTokenOnRedirect).open
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if dest_path.exists():
        if _sha256(dest_path) == sha256_expected:
            print(f"  already present: {dest_path.name}")
            return True
        dest_path.unlink()
    partial = dest_path.with_name(dest_path.name + ".part")
    start = partial.stat().st_size if partial.exists() else 0
    headers = {}
    if os.environ.get("HF_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["HF_TOKEN"]
    if start:
        headers["Range"] = f"bytes={start}-"
    try:
        response = opener(urllib.request.Request(url, headers=headers))
    except urllib.error.HTTPError as e:
        if e.code == 416:          # the partial file is already complete
            response = None
        elif e.code in (401, 403):
            print(f"  refused ({e.code}): {dest_path.name}. Accept the licence on Hugging Face and set HF_TOKEN.")
            return False
        else:
            print(f"  download failed ({e.code}): {dest_path.name}")
            return False
    except OSError as e:
        print(f"  download failed: {dest_path.name}: {e}")
        return False
    if response is not None:
        if start and getattr(response, "status", 200) != 206:
            start = 0              # the server ignored the Range header
        done = start
        with open(partial, "ab" if start else "wb") as out:
            while chunk := response.read(1024 * 1024):
                out.write(chunk)
                done += len(chunk)
                print(f"\r  {dest_path.name}: {done / 2**30:.2f} GB", end="", flush=True)
        print()
    if _sha256(partial) != sha256_expected:
        partial.unlink()
        print(f"  checksum mismatch, file deleted: {dest_path.name}")
        return False
    partial.replace(dest_path)
    return True


def link_nodes(src, dst):
    """Make the PSN nodes visible to ComfyUI: a symlink, or a copy where symlinks are not allowed (often Windows)."""
    src, dst = Path(src), Path(dst)
    if dst.exists() or dst.is_symlink():
        return
    try:
        dst.symlink_to(src, target_is_directory=True)
    except OSError:
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".git", "__pycache__", "venv", "tests"))


def comfy_flags(plan_result):
    flags = [f for i in plan_result["items"] if i["mode"] in ("gpu", "offload") for f in i.get("comfy_flags", [])]
    for f in ("--novram", "--lowvram"):
        if f in flags:
            return [f]
    return []


def launcher_text(system, base_dir, repo, flags, comfy_port=8200, studio_port=8310):
    base_dir, repo = Path(base_dir), Path(repo)
    models, output = base_dir / "ComfyUI" / "models", base_dir / "ComfyUI" / "output"
    comfy_input = base_dir / "ComfyUI" / "input"
    args = " ".join(["--listen", "127.0.0.1", "--port", str(comfy_port), *flags])
    if system == "Windows":
        py = base_dir / "venv" / "Scripts" / "python.exe"
        return ("@echo off\r\n"
                f'start "ComfyUI" /B "{py}" "{base_dir / "ComfyUI" / "main.py"}" {args}\r\n'
                f"set COMFYUI_URL=http://127.0.0.1:{comfy_port}\r\nset STUDIO_PORT={studio_port}\r\n"
                f'set "STUDIO_MODELS_ROOT={models}"\r\nset "PSN_MODELS_ROOT={models}"\r\n'
                f'set "STUDIO_OUTPUT_DIR={output}"\r\nset "STUDIO_COMFY_INPUT={comfy_input}"\r\n'
                f'cd /d "{repo}"\r\n"{py}" -m studio.server\r\n')
    py = base_dir / "venv" / "bin" / "python"
    return ("#!/bin/sh\n"
            f'"{py}" "{base_dir / "ComfyUI" / "main.py"}" {args} &\n'
            'COMFY_PID=$!\ntrap \'kill "$COMFY_PID"\' EXIT INT TERM\n'
            f"export COMFYUI_URL=http://127.0.0.1:{comfy_port} STUDIO_PORT={studio_port}\n"
            f'export STUDIO_MODELS_ROOT="{models}" PSN_MODELS_ROOT="{models}"\n'
            f'export STUDIO_OUTPUT_DIR="{output}" STUDIO_COMFY_INPUT="{comfy_input}"\n'
            f'cd "{repo}" && "{py}" -m studio.server\n')


def write_launcher(base_dir, flags):
    system = platform.system()
    path = Path(base_dir) / ("run_studio.bat" if system == "Windows" else "run_studio.sh")
    path.write_text(launcher_text(system, base_dir, REPO, flags), encoding="utf-8", newline="")
    if system != "Windows":
        path.chmod(0o755)
    return path


def print_goal_list(goal_manifest):
    for goal, entry in goal_manifest["goals"].items():
        size = sum(f["size_gb"] for f in entry["files"])
        gated = " [gated]" if any(f.get("gated") for f in entry["files"]) else ""
        print(f"{goal:12} {size:6.1f} GB{gated}  {entry.get('note', '')}")


def nearest_existing(path):
    """Disk space is measured where the install will land, even if that folder does not exist yet."""
    path = Path(path).resolve()
    while not path.exists():
        path = path.parent
    return path


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Install ComfyUI, the studio and the models that fit this machine.")
    p.add_argument("--channel", choices=["stable", "nightly"], default="stable",
                   help="stable pins the ComfyUI tag the studio was tested on; nightly follows ComfyUI master")
    p.add_argument("--dir", default=str(REPO.parent / "parametric-studio-runtime"),
                   help="where the venv, ComfyUI, models and launcher go (default: %(default)s)")
    p.add_argument("--goals", default="image",
                   help="comma-separated goals to fetch models for, or 'all' (default: image). See --list")
    p.add_argument("--include-gated", action="store_true", help="also fetch gated models; needs HF_TOKEN and an accepted licence")
    p.add_argument("--no-models", action="store_true", help="install the software only")
    p.add_argument("--yes", action="store_true", help="do not ask for confirmation; also allows running as root")
    p.add_argument("--dry-run", action="store_true", help="print the plan and every step, change nothing")
    p.add_argument("--profile-json", help="use a simulated hardware profile from this JSON file")
    p.add_argument("--list", action="store_true", help="list goals with download size and exit")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    goal_manifest = load_json(REPO / "studio" / "models_manifest.json")
    if args.list:
        print_goal_list(goal_manifest)
        return EXIT_OK
    if getattr(os, "geteuid", lambda: 1)() == 0 and not args.yes:
        print("Refusing to run as root without --yes.")
        return EXIT_CANCELLED
    profile = load_json(args.profile_json) if args.profile_json else detect(path=str(nearest_existing(args.dir)))
    print(describe(profile))

    plan_manifest = to_plan_manifest(goal_manifest)
    channels = load_json(REPO / "channels.json")
    wanted = None if args.goals == "all" else [g.strip() for g in args.goals.split(",") if g.strip()]
    unknown = [g for g in (wanted or []) if g not in goal_manifest["goals"]]
    if unknown:
        print(f"Unknown goal(s): {', '.join(unknown)}. See --list.")
        return EXIT_FAILED
    result = plan(profile, plan_manifest, wanted)
    for item in result["items"]:
        why = f" ({item['reason']})" if item.get("reason") else ""
        print(f"  {item['goal']:12} {item['mode']:12} about {item['est_vram_gb']:.0f} GiB VRAM{why}")
    for warning in result["warnings"]:
        print("  warning:", warning)
    files, skipped = selected_files(result, plan_manifest, args.include_gated)
    for goal, why in skipped:
        print(f"  skipping {goal}: {why}")
    if not args.no_models and not files:
        print("Nothing to download for these goals. Re-run with --no-models to install the software only, or pick other goals.")
        return EXIT_NOTHING
    size = 0.0 if args.no_models else sum(f["size_gb"] for f in files)
    print(f"Download: {size:.1f} GB of models into {Path(args.dir).resolve()}")

    cmds = build_commands(result, plan_manifest, channels, args.channel, args.dir, profile.get("backend", "cpu"),
                          args.include_gated, not args.no_models)
    if args.dry_run:
        for cmd in cmds:
            print(" ".join(map(str, cmd)))
        print("Then write the launcher. Dry run: nothing was changed.")
        return EXIT_OK
    if not args.yes and input("Proceed? [y/N] ").strip().lower() != "y":
        return EXIT_CANCELLED

    base_dir = Path(args.dir).resolve()
    base_dir.mkdir(parents=True, exist_ok=True)
    for cmd in cmds:
        print(">", cmd[0] if cmd[0] in ("download", "link") else " ".join(map(str, cmd[:4])), "...")
        if cmd[0] == "download":
            if not download_file(cmd[1], cmd[2], cmd[3]):
                return EXIT_FAILED
        elif cmd[0] == "link":
            link_nodes(cmd[1], cmd[2])
        else:
            try:
                subprocess.run(cmd, check=True)
            except (OSError, subprocess.CalledProcessError) as e:
                print(f"Step failed: {e}")
                return EXIT_FAILED
    launcher = write_launcher(base_dir, comfy_flags(result))
    print(f"Installed. Start it with: {launcher}\nThen open http://127.0.0.1:8310")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
