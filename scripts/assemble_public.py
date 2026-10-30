#!/usr/bin/env python3
"""Build the public release: an allow-listed copy of this checkout in a new folder, with a fresh `git init` and one commit. It never pushes and never adds a remote.
It then runs .github/scripts/repo_checks.py --public on the result (licences, secrets, excluded paths, private strings), and a fast test subset from a clean clone of it, with a throwaway HOME and no ComfyUI.
A real build only lands at --out when every check passes. An existing folder there is moved aside, never deleted.
Authorship: the commit carries a neutral identity. The script prints the command that sets yours; --use-git-identity uses this machine's git identity instead, only if you ask for it.
Usage: python scripts/assemble_public.py [--dry-run] [--out DIR] [--skip-tests] [--use-git-identity]     (use a Python that has pytest and fastapi)"""
import argparse, importlib.util, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = Path.home() / "public_release" / "ComfyUI_Parametric_Studio"
ALLOW_FILES = ("LICENSE", "NOTICE", "README.md", "INSTALL.md", "MODELS.md", "CONTRIBUTING.md", "SECURITY.md", "EDITIONS.md", "PROVENANCE.md", "THIRD_PARTY_NOTICES.md", "__init__.py", "install.py", "channels.json", "pyproject.toml", "uv.lock", "requirements.txt", "pytest.ini", ".gitignore")
ALLOW_DIRS = (".github/", "docs/", "psn/", "psn_nodes/", "scripts/", "studio/", "tests/", "workflows/")
NEUTRAL = ["-c", "user.name=Parametric Studio release", "-c", "user.email=release@parametric-studio.invalid"]
NEVER_IN_ALLOWED_DIRS = re.compile(r"(^|/)(__pycache__|\.pytest_cache)(/|$)|\.pyc$|\.log$|\.pid$|\.orig$|\.rej$|~$")


def load_checks(root=ROOT):
    spec = importlib.util.spec_from_file_location("repo_checks", root / ".github" / "scripts" / "repo_checks.py"); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod


def source_files(root=ROOT):
    """Tracked and untracked (not ignored) files of the checkout that exist right now."""
    out = subprocess.run(["git", "-C", str(root), "ls-files", "-co", "--exclude-standard", "-z"], capture_output=True, text=True, check=True).stdout
    return sorted({f for f in out.split("\0") if f and os.path.lexists(root / f)})


def select(files, excluded):
    """-> (kept, dropped by the exclusion rules, left out because they are not on the allow-list)."""
    keep, drop, off = [], [], []
    for f in files:
        if excluded(f) or NEVER_IN_ALLOWED_DIRS.search(f) or f in ("scripts/build_processes.py", "scripts/build_crew_notes.py", "scripts/build_family_art.py", "scripts/build_designer_art.py", "scripts/build_crew_art.py", "studio/printify.py"): drop.append(f)
        elif f in ALLOW_FILES or f.startswith(ALLOW_DIRS): keep.append(f)
        else: off.append(f)
    return keep, drop, off


def copy_tree(files, root, dest):
    for f in files:
        d = dest / f; d.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(root / f, d, follow_symlinks=False)


def git(tree, *args, identity=()):
    return subprocess.run(["git", "-C", str(tree), "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", *identity, *args], capture_output=True, text=True)


def fresh_commit(tree, use_identity=False):
    """A new repository with one commit and no remote. -> error text, or ''."""
    for args in (("init", "-q", "-b", "main"), ("add", "-A")):
        r = git(tree, *args)
        if r.returncode: return f"git {args[0]} failed: {r.stderr[:200]}"
    r = git(tree, "commit", "-q", "--no-verify", "-m", "Public release of ComfyUI_Parametric_Studio", identity=() if use_identity else NEUTRAL)
    return f"git commit failed: {r.stderr[:200]}" if r.returncode else ""


def fast_tests(tree):
    """The test files the CI workflow runs, read from ci.yml, so there is one list."""
    return sorted(set(re.findall(r"tests/[\w/]+\.py", (tree / ".github" / "workflows" / "ci.yml").read_text())))


def run_checks(tree, skip_tests=False, python=None, timeout=420):
    """-> list of failures. Runs the repo checks in the tree, the rest in a clean clone, so anything not committed counts as missing."""
    python = python or sys.executable; fails = []
    r = subprocess.run([python, "-B", ".github/scripts/repo_checks.py", "--public"], cwd=tree, capture_output=True, text=True, timeout=120)
    print(r.stdout.rstrip()); print(r.stderr.rstrip()[-400:]) if r.stderr.strip() else None
    if r.returncode: fails.append("repo_checks.py --public")
    if not (Path(os.environ.get("PSN_PRIVATE_STRINGS") or Path.home() / ".config/parametric-studio/private_strings.txt")).is_file(): print("note: no off-repo private string list on this machine; only the generic patterns ran")
    if skip_tests: print("TESTS SKIPPED (--skip-tests): the tree has not been proven from a clean clone"); return fails
    for need in ("pytest", "fastapi", "httpx"):
        if subprocess.run([python, "-c", f"import {need}"], capture_output=True).returncode: return fails + [f"{python} cannot import {need}: run this script with the project's Python, or pass --skip-tests"]
    with tempfile.TemporaryDirectory(prefix="psn_public_clone_") as tmp:
        clone, home = Path(tmp) / "clone", Path(tmp) / "home"; home.mkdir()
        r = subprocess.run(["git", "clone", "-q", str(tree), str(clone)], capture_output=True, text=True)
        if r.returncode: return fails + [f"git clone failed: {r.stderr[:200]}"]
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(home), "LANG": "C.UTF-8", "COMFYUI_URL": "http://127.0.0.1:9", "PYTHONDONTWRITEBYTECODE": "1"}
        tests = fast_tests(clone)
        steps = [("fast tests", [python, "-m", "pytest", "-q", "-p", "no:cacheprovider", *tests]), ("server import with ComfyUI unreachable", [python, "-c", "import studio.server as s; print(len(s.app.routes), 'routes')"]),
                 ("installer dry run", [python, "install.py", "--dry-run", "--no-models", "--dir", str(Path(tmp) / "rt")])]
        for name, cmd in steps:
            t0 = time.time()
            try: r = subprocess.run(cmd, cwd=clone, env=env, capture_output=True, text=True, timeout=timeout); out, rc = (r.stdout + r.stderr), r.returncode
            except subprocess.TimeoutExpired: out, rc = f"timed out after {timeout} s", 1
            last = [l for l in out.strip().splitlines() if l.strip()][-1:] or [""]
            print(f"{name}: {'ok' if not rc else 'FAILED'} in {time.time() - t0:.0f} s: {last[0][:160]}")
            if rc:
                fails.append(name); print("\n".join(l[:200] for l in out.strip().splitlines() if re.match(r"(FAILED|ERROR|E  )", l))[:3000])
    return fails


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the public release tree. Never pushes.")
    ap.add_argument("--dry-run", action="store_true", help="build and check in a temporary folder; write nothing at --out")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT); ap.add_argument("--skip-tests", action="store_true"); ap.add_argument("--use-git-identity", action="store_true", help="commit with this machine's git identity instead of the neutral one")
    a = ap.parse_args(argv); out = a.out.expanduser().resolve()
    if out == ROOT or ROOT in out.parents: print("--out must be outside this checkout"); return 2
    checks = load_checks(); files = source_files(); keep, drop, off = select(files, checks.excluded)
    dirty = [l[3:] for l in subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=all"], capture_output=True, text=True).stdout.splitlines() if l[3:] in keep]
    head = subprocess.run(["git", "-C", str(ROOT), "log", "-1", "--format=%h"], capture_output=True, text=True).stdout.strip()
    print(f"source: this checkout at {head}; {len(keep)} files go in, {len(drop)} excluded by rule, {len(off)} not on the allow-list")
    for f in off[:20]: print(f"  not on the allow-list, left out: {f}")
    if dirty: print(f"  note: {len(dirty)} of the files going in are not committed in the source (copied as they are on disk); first: {', '.join(dirty[:5])}")
    missing = [f for f in ("LICENSE", "NOTICE", "README.md", "install.py", ".github/scripts/repo_checks.py", ".github/workflows/ci.yml", "scripts/assemble_public.py") if f not in keep]
    if missing: print("FAILED: required files are not in the selection:", ", ".join(missing)); return 1
    stamp = time.strftime("%Y%m%d-%H%M%S"); tmpdir = None
    if a.dry_run: tmpdir = tempfile.TemporaryDirectory(prefix="psn_public_dry_"); tree = Path(tmpdir.name) / out.name
    else: out.parent.mkdir(parents=True, exist_ok=True); tree = out.parent / f"{out.name}.building-{stamp}"
    tree.mkdir(); copy_tree(keep, ROOT, tree)
    err = fresh_commit(tree, a.use_git_identity); fails = [err] if err else run_checks(tree, a.skip_tests)
    if git(tree, "remote").stdout.strip(): fails.append("the new repository has a remote")
    size = sum(f.stat().st_size for f in tree.rglob("*") if f.is_file() and ".git" not in f.relative_to(tree).parts) / 2**20
    print(f"tree: {len(keep)} files, {size:.0f} MB, one commit, no remote, nothing pushed")
    if a.dry_run:
        tmpdir.cleanup(); print("DRY RUN " + ("FAILED: " + "; ".join(fails) if fails else f"OK: every check passed. Nothing was written at {out}")); return 1 if fails else 0
    if fails:
        bad = out.parent / f"{out.name}.FAILED-{stamp}"; tree.rename(bad); print(f"FAILED: {'; '.join(fails)}\nThe failed tree is at {bad}. Nothing was written at {out}."); return 1
    if out.exists(): old = out.parent / f"{out.name}.previous-{stamp}"; out.rename(old); print(f"moved the earlier build aside to {old}")
    tree.rename(out); print(f"OK: public tree at {out}")
    if not a.use_git_identity: print(f"Set your own authorship (neutral identity for now):\n  git -C {out} -c user.name=\"YOUR NAME\" -c user.email=\"YOUR EMAIL\" commit --amend --reset-author --no-edit")
    print(f"This script does not push. When you are ready, add your remote and push from {out} yourself."); return 0


if __name__ == "__main__":
    sys.exit(main())
