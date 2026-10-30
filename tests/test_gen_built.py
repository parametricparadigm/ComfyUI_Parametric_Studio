"""Every merged builder module keeps its own plain-assert test (tests/gen_built/<slug>/test_<slug>.py). They run here in parallel subprocesses on CPU (GPU hidden), each with psn_nodes/gen on the path."""
import concurrent.futures as cf, glob, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def run(t):
    d = os.path.dirname(t); env = {"PATH": "/usr/bin:/bin", "CUDA_VISIBLE_DEVICES": "", "OMP_NUM_THREADS": "2", "HOME": d, "PYTHONPATH": os.path.join(ROOT, "psn_nodes", "gen")}
    try: p = subprocess.run([sys.executable, "-B", t], cwd=d, capture_output=True, text=True, timeout=240, env=env); ok = p.returncode == 0 and "ok" in p.stdout; return os.path.basename(d), ok, (p.stderr.strip().splitlines() or p.stdout.strip().splitlines() or [""])[-1][:120]
    except subprocess.TimeoutExpired: return os.path.basename(d), False, "timeout"
def test_all_merged_builder_modules_pass_their_own_tests():
    tests = sorted(glob.glob(os.path.join(ROOT, "tests", "gen_built", "*", "test_*.py")))
    if not tests: return
    with cf.ThreadPoolExecutor(8) as ex: res = list(ex.map(run, tests))
    bad = [f"{s}: {m}" for s, ok, m in res if not ok]
    assert not bad, f"{len(bad)} of {len(res)} failed: " + "; ".join(bad[:6])
def test_every_merged_module_is_listed_in_the_manifest():
    import csv
    m = {r["slug"] for r in csv.DictReader(open(os.path.join(ROOT, "psn_nodes", "gen", "BUILT_MANIFEST.tsv")), delimiter="\t") if r["decision"] == "merged"}
    on_disk = {os.path.basename(os.path.dirname(t)) for t in glob.glob(os.path.join(ROOT, "tests", "gen_built", "*", "test_*.py"))}
    assert on_disk <= m, sorted(on_disk - m)[:5]
