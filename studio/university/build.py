#!/usr/bin/env python3
"""ComfyUniversity builder. Lessons live here, one folder per course: <level>/<code>-<slug>/{course.json, lesson.md, lab.py, lab_output.txt, quiz.json}.
python studio/university/build.py            checks every lesson, writes catalogue.json and CATALOGUE.md
python studio/university/build.py --labs     also runs every lab twice on the CPU, requires identical output and under 60 s, stores lab_output.txt
python studio/university/build.py --labs --only CU-101 CU-102
Standard library only, plus torch inside the labs themselves."""
import argparse, concurrent.futures as cf, json, os, re, subprocess, sys, tempfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent; LIMIT = 60
META = lambda: json.loads((HERE / "meta.json").read_text()); SOURCES = lambda: json.loads((HERE / "sources.json").read_text())
LAB_IMPORTS = {"torch", "math", "random", "json", "itertools", "collections", "struct", "zlib", "io", "hashlib", "heapq", "functools", "re", "dataclasses", "typing", "base64", "asyncio", "pickle", "copy"}
REQUIRED = ["Objective", "## Lab", "## Sources"]

def courses():
    """Every course folder on disk, in teaching order: level, then the code. status "draft" means imported from the earlier model-written set and not yet audited."""
    rows = []
    for f in HERE.glob("[1-4]00/CU-*/course.json"):
        c = json.loads(f.read_text()); c["path"] = str(f.parent.relative_to(HERE)); c["dir"] = f.parent; rows.append(c)
    return sorted(rows, key=lambda c: (c["level"], c["code"]))

def lab_env(threads=1): return {"PATH": "/usr/bin:/bin", "CUDA_VISIBLE_DEVICES": "", "OMP_NUM_THREADS": str(threads), "MKL_NUM_THREADS": str(threads), "PYTHONHASHSEED": "0", "HOME": tempfile.gettempdir()}

def run_lab(path, py=None, timeout=LIMIT):
    """Run one lab in a throw-away folder with no GPU. -> (ok, stdout, seconds, stderr tail)."""
    code = Path(path).read_text(); t = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="cu_lab_") as wd:
        (Path(wd) / "lab.py").write_text(code)
        try: p = subprocess.run([py or sys.executable, "-I", "lab.py"], cwd=wd, capture_output=True, text=True, timeout=timeout, env=lab_env())
        except subprocess.TimeoutExpired: return False, "", time.perf_counter() - t, f"timed out after {timeout} s"
    return p.returncode == 0, p.stdout, time.perf_counter() - t, "\n".join(p.stderr.splitlines()[-12:])

def lab_imports(code): return {m.split(".")[0] for m in re.findall(r"^\s*(?:import|from)\s+([\w.]+)", code, re.M)}

def quiz_right(q, o, i):
    """The same rule the web page uses to mark an option right (Quiz in studio/web/app.js)."""
    a = str(q.get("answer") or "").strip(); lo = o.lower(); la = a.lower()
    return a == o or la.startswith(chr(97 + i) + ")") or la.startswith(chr(97 + i) + ".") or a == chr(65 + i) or (len(a) > 3 and la in lo) or (len(o) > 3 and lo in la)

def lesson_links(md): return re.findall(r"\[([^\]]+)\]\((https?:[^)\s]+)\)", md)

def check_course(c, codes, sources):
    """-> list of problems with one course. Everything here is checked again by tests/test_university.py."""
    d = c["dir"]; pr = []; md = (d / "lesson.md").read_text() if (d / "lesson.md").exists() else ""
    for n in ("lesson.md", "lab.py", "lab_output.txt", "quiz.json"):
        if not (d / n).exists(): pr.append("missing " + n)
    if pr: return pr
    if not md.startswith(f"# {c['code']} - {c['title']}\n"): pr.append("first line must be the code and title")
    for s in REQUIRED:
        if s not in md: pr.append("lesson lacks " + s)
    if re.search(r"\$[^$\n]{1,80}\$|\\frac|\\sigma|\\epsilon", md): pr.append("LaTeX in lesson: the page has no maths renderer, write Unicode")
    prose = re.sub(r"```.*?```", "", md, flags=re.S); prose = prose.replace("**", "")
    if "*" in prose: pr.append("stray * in prose: the page's markdown would turn it into emphasis")
    for w in ("UNVERIFIED", "Qwen3.8", "/" + "mnt/fast", "/" + "home/"):
        if w in md: pr.append("banned text in lesson: " + w)
    links = lesson_links(md[md.find("## Sources"):])
    if not links: pr.append("no linked sources")
    for _, u in links:
        if u.rstrip("/") not in sources: pr.append("source not in sources.json: " + u)
    out = (d / "lab_output.txt").read_text().splitlines(); lab = md[md.find("## Lab"):]; lab = lab[:lab.find("\n## ", 6)]
    for block in re.findall(r"```text\n(.*?)```", lab, re.S):
        for l in block.splitlines():
            if l.strip() and l.strip() != "..." and l.rstrip() not in [x.rstrip() for x in out]: pr.append("lab line not in lab_output.txt: " + l[:70])
    bad = lab_imports((d / "lab.py").read_text()) - LAB_IMPORTS
    if bad: pr.append(f"lab imports {sorted(bad)}")
    if "assert " not in (d / "lab.py").read_text(): pr.append("lab has no assert")
    qs = json.loads((d / "quiz.json").read_text()).get("questions", [])
    if len(qs) < 3: pr.append("fewer than 3 quiz questions")
    for q in qs:
        if not q.get("why"): pr.append("quiz answer without a reason: " + q["q"][:50])
        if q.get("options"):
            right = [o for i, o in enumerate(q["options"]) if quiz_right(q, o, i)]
            if len(right) != 1: pr.append(f"quiz question marks {len(right)} options right: " + q["q"][:50])
    for p in c.get("prereq", []):
        if p not in codes: pr.append("unknown prerequisite " + p)
    return pr

def complete(c): return all((c["dir"] / n).exists() for n in ("lesson.md", "lab.py", "lab_output.txt", "quiz.json")) and bool(json.loads((c["dir"] / "quiz.json").read_text()).get("questions"))

def write_catalogue(rows, meta):
    """Only finished lessons reach the page. A course folder still missing its lesson or quiz stays off the catalogue."""
    pub = [{**{k: c[k] for k in ("code", "title", "level", "prereq", "char", "hook")}, "status": c.get("status", "audited"), "path": c["path"]} for c in rows if complete(c)]
    (HERE / "catalogue.json").write_text(json.dumps({"levels": meta["levels"], "characters": meta["characters"], "courses": pub}, indent=1, ensure_ascii=False) + "\n")
    with open(HERE / "CATALOGUE.md", "w") as f:
        f.write("# ComfyUniversity course catalogue\n\nEvery lesson has a CPU lab with stored output, a quiz, and linked primary sources. Rebuild with `python studio/university/build.py --labs`.\n")
        for lv, name in meta["levels"].items():
            f.write(f"\n## Level {lv}: {name}\n\n")
            for c in pub:
                if c["level"] == lv: f.write(f"- **{c['code']}** [{c['title']}]({c['path']}/lesson.md). {c['hook']}" + (f" Needs {', '.join(c['prereq'])}." if c["prereq"] else "") + "\n")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--labs", action="store_true"); ap.add_argument("--only", nargs="*", default=[]); ap.add_argument("--workers", type=int, default=6); ap.add_argument("--py", default=sys.executable); a = ap.parse_args()
    rows = courses(); codes = {c["code"] for c in rows}; bad = 0
    if a.labs:
        todo = [c for c in rows if not a.only or c["code"] in a.only]
        def one(c):
            r1 = run_lab(c["dir"] / "lab.py", a.py); r2 = run_lab(c["dir"] / "lab.py", a.py) if r1[0] else r1
            ok = r1[0] and r2[0] and r1[1] == r2[1] and max(r1[2], r2[2]) < LIMIT
            if ok: (c["dir"] / "lab_output.txt").write_text(r1[1])
            return c, ok, r1, r2
        with cf.ThreadPoolExecutor(a.workers) as ex:
            for c, ok, r1, r2 in ex.map(one, todo):
                print(f"{c['code']} lab {'ok' if ok else 'FAILED'} {max(r1[2], r2[2]):.1f} s" + ("" if ok else ("\n" + r1[3] if not r1[0] else " output differs between runs" if r1[1] != r2[1] else " too slow")), flush=True); bad += not ok
    sources = {k.rstrip("/"): v for k, v in SOURCES().items()}
    for c in rows:
        if c.get("status") == "draft" and not complete(c): print(c["code"], "draft is incomplete, left off the catalogue"); continue
        if c.get("status") == "draft": continue
        if not complete(c): print(c["code"], "not finished, left off the catalogue"); continue
        for p in check_course(c, codes, sources): print(c["code"], p); bad += 1
    write_catalogue(rows, META()); print(f"{len(rows)} courses, {bad} problems"); sys.exit(1 if bad else 0)

if __name__ == "__main__": main()
