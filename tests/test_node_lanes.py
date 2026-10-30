"""Runs the plain-node (.mjs) tests of the studio front-end modules in a temp copy of studio/web (so relative imports resolve); skipped when node is not installed."""
import glob, os, shutil, subprocess, tempfile, pytest
HERE = os.path.dirname(__file__); WEB = os.path.join(HERE, "..", "studio", "web")
@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
@pytest.mark.parametrize("path", sorted(glob.glob(os.path.join(HERE, "studio_lanes", "test_*.mjs"))))
def test_node_module(path):
    with tempfile.TemporaryDirectory() as d:
        for f in glob.glob(os.path.join(WEB, "*.js")): shutil.copy(f, d)
        shutil.copy(path, d)
        p = subprocess.run(["node", os.path.join(d, os.path.basename(path))], cwd=d, capture_output=True, text=True, timeout=60)
    assert p.returncode == 0 and p.stdout.split()[-1:] == ["ok"], p.stdout + p.stderr
