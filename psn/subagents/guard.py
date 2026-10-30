"""Guardrails for subagent tools (ported from the studio's Qwen tool loop). Best-effort filtering (NOT an OS sandbox: user namespaces are blocked on this box,
so bubblewrap is unavailable). Rule of thumb: when in doubt it denies. Tested by test_guard.py."""
import os, re, shlex, threading
_T = threading.local()   # base directory for relative paths in the command being checked

CRED_RX = re.compile(
    r"(credentials|\.ssh|\.gnupg|\.aws|\.netrc|\.pgpass|\.git-credentials|rclone\.conf|\.config/rclone|\.claude\.json|"
    r"\.credentials\.json|id_rsa|id_ed25519|\.pem$|\.p12$|\.pfx$|(^|/)\.env($|\.)|(^|/)auth\.json$|\.npmrc|\.pypirc|/proc/[^/]+/environ)", re.I)
SECRET_VAR_RX = re.compile(r"\$\{?[A-Za-z_]*(KEY|TOKEN|SECRET|PASS|AUTH|CRED)[A-Za-z_]*", re.I)

DENY_CMDS = set("""rm rmdir unlink shred mv dd mkfs mkfs.ext4 truncate fallocate sudo su doas mount umount chmod chown chgrp ln
kill pkill killall reboot shutdown halt poweroff pip pip3 pipx uv conda mamba npm npx yarn pnpm apt apt-get dpkg snap
docker podman crontab at nc ncat socat ssh scp rsync sftp ftp rclone wget env printenv export set declare unset eval exec
source . sh bash zsh dash fish xargs nohup setsid command builtin timeout time nice watch ollama llama-swap perl ruby node
php lua tclsh gdb strace ltrace patch install useradd userdel passwd crontab systemd-run loginctl nvidia-persistenced""".split())
SYSTEMCTL_OK = {"status", "is-active", "is-enabled", "is-failed", "list-units", "list-unit-files", "cat", "show", "list-timers", "list-sockets"}
GIT_OK = {"status", "log", "diff", "show", "branch", "ls-files", "rev-parse", "remote", "blame", "describe", "shortlog", "ls-tree", "cat-file"}
NVSMI_BAD = {"-r", "--gpu-reset", "-pm", "-pl", "-lgc", "-rgc", "-c", "-e", "-acp", "-ac", "-rac", "--compute-mode", "-mig", "-lmc", "-rmc", "-sc"}
CURL_BAD = re.compile(r"^(-o|-O|--output|-T|--upload-file|-d|--data.*|-X|--request|-F|--form|-K|--config|-u|--user|--netrc.*|-b|-c|--cookie.*|--json)$")


def _real(p):
    p = os.path.expanduser(p)
    base = getattr(_T, 'cwd', None)
    if base and not os.path.isabs(p): p = os.path.join(base, p)
    return os.path.realpath(p)


def _under(p, roots):
    rp = _real(p)
    return any(rp == r or rp.startswith(r.rstrip("/") + "/") for r in roots)


def check_read(path):
    if CRED_RX.search(_real(path)) or CRED_RX.search(str(path)):
        return False, "credential/secret locations are off limits"
    return True, ""


def check_write(path, roots):
    ok, why = check_read(path)
    if not ok: return ok, why
    if not _under(path, roots):
        return False, f"writes are only allowed under {roots}"
    return True, ""


def _segments(cmd):
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    toks = list(lex)
    segs, cur = [], []
    for t in toks:
        if t in (";", "&&", "||", "|", "&", "|&", "\n"):
            if cur: segs.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur: segs.append(cur)
    return segs


def check_bash(cmd, roots, cwd=None):
    _T.cwd = cwd
    try: return _check_bash(cmd, roots)
    finally: _T.cwd = None


def _check_bash(cmd, roots):
    if "\x00" in cmd: return False, "bad input"
    if CRED_RX.search(cmd): return False, "mentions a credential/secret location"
    if SECRET_VAR_RX.search(cmd): return False, "secret-looking variable"
    if "`" in cmd or "$(" in cmd or "<(" in cmd or ">(" in cmd: return False, "command substitution is not allowed; run steps separately"
    if "<<" in cmd: return False, "heredocs are not allowed; use write_file"
    if "/unload" in cmd or "/api/stop" in cmd: return False, "server/model control endpoints are off limits"
    try:
        segs = _segments(cmd)
    except ValueError as e:
        return False, f"cannot parse command: {e}"
    if not segs: return False, "empty command"
    for seg in segs:
        # redirects
        i = 0
        while i < len(seg):
            t = seg[i]
            if re.match(r"^\d*(>>?|>\||&>>?)$", t) or t in (">", ">>"):
                tgt = seg[i + 1] if i + 1 < len(seg) else ""
                if tgt != "/dev/null" and not _under(tgt, roots):
                    return False, f"redirect target {tgt!r} is outside the write roots"
                i += 1
            elif re.match(r"^\d*>&$", t):
                i += 1  # fd duplication like 2>&1
            i += 1
        words = [t for t in seg if not re.match(r"^\d*(>>?|>\||&>>?|>&|<)$", t)]
        # drop leading VAR=value
        while words and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[0]): words.pop(0)
        if not words: continue
        name = os.path.basename(words[0])
        args = words[1:]
        if name in DENY_CMDS: return False, f"command {name!r} is not allowed"
        if name == "find" and any(a in ("-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint", "-fprint0", "-fls", "-fprintf") for a in args):
            return False, "find with -delete/-exec/-fprint is not allowed"
        if name == "sed" and any(a == "-i" or a.startswith("-i") or a.startswith("--in-place") for a in args):
            return False, "sed -i edits files; use edit_file"
        if name in ("awk", "gawk", "mawk") and any("system(" in a or "getline" in a for a in args):
            return False, "awk system()/getline is not allowed"
        if name.startswith("python"):
            fl = [a for a in args if a.startswith("-")]
            rest = [a for a in args if not a.startswith("-")]
            if args[:2] == ["-m", "json.tool"] or args == ["--version"] or args == ["-V"]:
                continue
            if any(f not in ("-I", "-u", "-B", "-E", "-s", "-S") for f in fl):
                return False, "python is only allowed as: python3 [-I -u -B] <script.py inside the write roots>"
            if not rest or not rest[0].endswith(".py") or not _under(rest[0], roots):
                return False, "python only runs .py scripts located inside the write roots"
            continue
        if name == "systemctl":
            sub = [a for a in args if not a.startswith("-")]
            if not sub or sub[0] not in SYSTEMCTL_OK: return False, "systemctl: read-only subcommands only (status, is-active, cat, show, list-*)"
        elif name == "journalctl":
            if any(a in ("--vacuum-size", "--vacuum-time", "--vacuum-files", "--rotate", "--flush", "--sync") or a.startswith("--vacuum") for a in args):
                return False, "journalctl maintenance flags are not allowed"
        elif name == "git":
            ga, sub, j = list(args), [], 0
            while j < len(ga):
                if ga[j] == "-C" and j + 1 < len(ga): j += 2; continue
                if ga[j] == "-c": return False, "git -c (config override) is not allowed"
                if not ga[j].startswith("-"): sub.append(ga[j])
                j += 1
            if not sub or sub[0] not in GIT_OK: return False, "git: read-only subcommands only"
            if sub[0] in ("branch", "remote") and any(a in ("-d", "-D", "-m", "-M", "add", "remove", "rm", "set-url", "rename", "-c", "-C", "--delete") for a in args):
                return False, "git branch/remote modifications are not allowed"
        elif name == "curl":
            if any(CURL_BAD.match(a) for a in args): return False, "curl: GET only, no output files, uploads or auth"
        elif name == "nvidia-smi":
            if any(a in NVSMI_BAD for a in args): return False, "nvidia-smi: query only"
        elif name in ("tee", "touch", "mkdir"):
            paths = [a for a in args if not a.startswith("-")]
            for p in paths:
                if not _under(p, roots): return False, f"{name} target {p!r} is outside the write roots"
        elif name == "cp":
            if any(a in ("-t", "--target-directory") or a.startswith("--target-directory") for a in args): return False, "cp -t is not allowed"
            paths = [a for a in args if not a.startswith("-")]
            if len(paths) < 2 or not _under(paths[-1], roots): return False, "cp destination must be inside the write roots"
        elif name == "tar":
            flags = "".join(a.lstrip("-") for a in args if a.startswith("-") or re.match(r"^[a-zA-Z]+$", a))
            if not re.search(r"t", flags) or re.search(r"[xcru]", flags.replace("--", "")): return False, "tar: listing (-t) only"
        elif name in ("unzip", "7z", "7za"):
            if not any(a in ("-l", "l") for a in args): return False, f"{name}: listing only"
        elif name in ("script", "screen", "tmux", "vim", "vi", "nano", "emacs", "less", "more"):
            return False, f"{name} is interactive"
        # any argument that is an existing path we can resolve must not be a credential
        for a in args:
            if CRED_RX.search(a): return False, "argument mentions a credential/secret location"
    return True, ""
