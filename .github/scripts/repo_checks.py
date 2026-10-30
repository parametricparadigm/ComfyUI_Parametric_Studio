#!/usr/bin/env python3
"""Repository checks with no dependencies: licence files, conflicting licence claims, secrets, private paths.
With --public it also holds the public release to its rules: no excluded path may be tracked, and no private string may appear anywhere in the tree.
Private strings: generic patterns here, plus an optional list kept off the repo ($PSN_PRIVATE_STRINGS or ~/.config/parametric-studio/private_strings.txt, one per line).
Findings name the file, line and pattern only, so a secret never reaches the CI log."""
import hashlib, os, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AGPL_SHA256 = "0d96a4ff68ad6d4b6f1f30f713b18d5184912ba8dd389f86aa7710db079abcb0"  # gnu.org/licenses/agpl-3.0.txt
VENDOR_LICENCES = ["studio/web/vendor/LICENSE-preact.txt", "studio/web/vendor/LICENSE-htm.txt", "studio/web/vendor/LICENSE-three.txt",
                   "psn/subagents/playbooks/LICENSE-awesome-claude-agents.txt", "studio/web/vendor/fonts/LICENSE-Archivo-OFL.txt", "studio/web/vendor/fonts/LICENSE-Inter-OFL.txt"]
SECRETS = {"hf_token": r"\bhf_[A-Za-z0-9]{30,}\b", "github_token": r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36}\b|\bgithub_pat_[A-Za-z0-9_]{40,}",
           "private_key": r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "aws_key": r"\bAKIA[0-9A-Z]{16}\b", "google_key": r"\bAIza[0-9A-Za-z_\-]{35}\b"}
SKIP_SECRETS = ("tests/", "extended_candidates/tests/")     # fixtures carry fake keys on purpose
CONFLICT = re.compile(r"SPDX-License-Identifier:\s*(?!AGPL-3\.0)|Licensed under the (?:MIT|Apache) License")
CONFLICT_DIRS = ("psn/", "psn_nodes/", "studio/", "scripts/")
CONFLICT_SKIP = ("studio/web/vendor/", "psn/subagents/playbooks/", "studio/skills/")
BOX_PATH = "/" + r"mnt/fast\b|/" + r"home/(?!user\b|username\b|you\b|me\b|runner\b|ubuntu\b|name\b|comfy\b)[a-z_][a-z0-9_-]*/"     # any real home folder, or this project's model disk
PRIVATE = re.compile(BOX_PATH)
PRIVATE_DOCS = ("README.md", "INSTALL.md", "MODELS.md", "CONTRIBUTING.md", "SECURITY.md", "docs/")
# The public release leaves these out (scripts/assemble_public.py reads this list too). Any of them tracked in the public repo is a leak.
EXCLUDED = ("docs/superpowers/", "docs/SUBMISSION.md", "docs/DEMO_SCRIPT.md", ".superpowers/", "studio/atlas.json", "studio/skills/", "extended_candidates/")
EXCLUDED_PARTS = (".cache", "__pycache__", ".pytest_cache", ".benchmarks", ".deepeval", ".env")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
EMAIL_OK = re.compile(r"@(?:[\w-]+\.)*(?:example\.(?:com|org|net)|example|test|invalid|localhost|api\.telegram\.org|github\.com|users\.noreply\.github\.com)$|\.service$|\.(?:png|jpe?g|webp|svg|js|mjs|css)$", re.I)
PRIVATE_TEXT = {"business rate": r"\$\s?\d[\d,.]*\s?(?:/|per\s)\s?(?:hr|hour|day|mo|month|min|video|post|sub)\b", "owner's dated note": r"\bowner 20\d\d-\d\d", "private library entry": r"yt-thumbnail-brief",
                "shop id": r"\b(?:shop|store|seller)[_ -]?id\s*[:=]\s*\S+|\b[\w-]+\.myshopify\.com\b"}
EMAIL_SKIP = ("studio/web/vendor/", "psn/subagents/playbooks/")      # third-party text carries its authors' and its examples' addresses


def excluded(f):
    """True when a repo-relative path must stay out of the public release."""
    return f.startswith(EXCLUDED) or any(part in EXCLUDED_PARTS or part.startswith(".env") for part in f.split("/"))


def private_list(path=None):
    p = path or os.environ.get("PSN_PRIVATE_STRINGS") or os.path.expanduser("~/.config/parametric-studio/private_strings.txt")
    try: return [x.strip().lower().encode() for x in open(p, encoding="utf-8", errors="ignore") if x.strip() and not x.startswith("#")]
    except OSError: return []


def public_problems(root, files, deny=None):
    """Findings for a public tree: excluded paths, box paths and listed strings in any file (binary too), emails and business notes in text files. Names the file, line and pattern only."""
    out, deny = [], private_list() if deny is None else deny
    rx = {k: re.compile(v, re.I) for k, v in PRIVATE_TEXT.items()}; box = re.compile(BOX_PATH.encode())
    for f in files:
        if excluded(f): out.append(f"{f}: excluded path is in the public tree")
        path = Path(root) / f
        if path.is_symlink():
            t = os.readlink(path)
            if os.path.isabs(t) or not os.path.realpath(path).startswith(os.path.realpath(root) + os.sep): out.append(f"{f}: symlink leaves the tree")
            continue
        if not path.is_file(): continue
        b = path.read_bytes(); low = b.lower(); binary = b"\0" in b[:8192]
        if f == ".github/scripts/repo_checks.py": continue      # holds the patterns themselves
        out += [f"{f}: listed private string #{i}" for i, t in enumerate(deny, 1) if re.search(rb"(?<![a-z0-9])" + re.escape(t) + rb"(?![a-z0-9])", low)]
        if binary:
            if box.search(b): out.append(f"{f}: box path inside a binary file")
            continue
        for n, line in enumerate(b.decode("utf-8", "ignore").splitlines(), 1):
            if box.search(line.encode()): out.append(f"{f}:{n}: box path")
            out += [f"{f}:{n}: looks like a {k}" for k, r in rx.items() if r.search(line)]
            if not f.startswith(EMAIL_SKIP) and any(not EMAIL_OK.search(m) for m in EMAIL.findall(line)): out.append(f"{f}:{n}: email address")
    return out


def tracked():
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"], capture_output=True, text=True, check=True).stdout
    return [f for f in out.split("\0") if f]


def main(argv=None):
    public = "--public" in (sys.argv[1:] if argv is None else argv); problems = []
    if hashlib.sha256((ROOT / "LICENSE").read_bytes()).hexdigest() != AGPL_SHA256:
        problems.append("LICENSE: not the unmodified AGPL-3.0 text")
    problems += [f"{f}: vendored licence file is missing" for f in VENDOR_LICENCES if not (ROOT / f).is_file()]
    rx = {k: re.compile(v) for k, v in SECRETS.items()}
    for f in tracked():
        path = ROOT / f
        if not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for n, line in enumerate(lines, 1):
            if not f.startswith(SKIP_SECRETS):
                problems += [f"{f}:{n}: looks like {k}" for k, r in rx.items() if r.search(line)]
            if f.startswith(CONFLICT_DIRS) and not f.startswith(CONFLICT_SKIP) and f.endswith(".py") and CONFLICT.search(line):
                problems.append(f"{f}:{n}: licence claim that is not AGPL-3.0")
            if f.startswith(PRIVATE_DOCS) and PRIVATE.search(line):
                problems.append(f"{f}:{n}: private path in the docs")
    if public: problems += public_problems(ROOT, tracked())
    for p in problems:
        print(p)
    print(f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
