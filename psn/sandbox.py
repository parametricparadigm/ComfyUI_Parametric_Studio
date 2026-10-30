"""Run LLM-written or user-written Python in a separate, resource-limited process and get back only data. See sandbox_runner.py for what is blocked.
Limits: wall-clock timeout (process group killed), CPU seconds, address space, open files, file size, no core dumps, empty environment, throw-away working directory."""
import os, sys, json, time, signal, tempfile, subprocess, resource

RUNNER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sandbox_runner.py")
MARK = "@@PSN_RESULT@@"

def run(code, inputs=None, timeout=10.0, mem_mb=512, allow=None, max_stdout=2_000_000):
    """-> {"ok": bool, "result": ..., "stdout": str, "error": str, "secs": float, "timed_out": bool}"""
    timeout = max(0.5, min(float(timeout), 120.0)); mem = int(max(64, min(int(mem_mb), 4096))) * 1024 * 1024
    payload = json.dumps({"code": code, "inputs": inputs, "allow": list(allow) if allow else None})
    def limits():
        resource.setrlimit(resource.RLIMIT_AS, (mem, mem)); resource.setrlimit(resource.RLIMIT_CPU, (int(timeout) + 2, int(timeout) + 2))
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64)); resource.setrlimit(resource.RLIMIT_FSIZE, (1 << 20, 1 << 20)); resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="psn_sbx_") as wd:
        p = subprocess.Popen([sys.executable, "-I", "-S", RUNNER], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=wd, env={"PATH": "/usr/bin:/bin", "PYTHONHASHSEED": "0", "HOME": wd},
                             preexec_fn=limits, start_new_session=True, text=True)
        try: out, err = p.communicate(payload, timeout=timeout)
        except subprocess.TimeoutExpired:
            try: os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            p.communicate(); return {"ok": False, "result": None, "stdout": "", "error": f"timed out after {timeout:g}s", "secs": time.time() - t0, "timed_out": True}
        finally:
            try: os.killpg(p.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError): pass
    out = (out or "")[:max_stdout]; i = out.rfind(MARK)
    if i < 0: return {"ok": False, "result": None, "stdout": "", "error": ("crashed: " + (err or "").strip()[-300:]) if (err or "").strip() else f"no result (exit code {p.returncode}; likely a memory or CPU limit)", "secs": time.time() - t0, "timed_out": False}
    try: d = json.loads(out[i + len(MARK):].strip())
    except json.JSONDecodeError: return {"ok": False, "result": None, "stdout": "", "error": "unreadable result", "secs": time.time() - t0, "timed_out": False}
    return {"ok": bool(d.get("ok")), "result": d.get("result"), "stdout": d.get("stdout", ""), "error": d.get("error", ""), "secs": time.time() - t0, "timed_out": False}
