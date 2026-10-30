import os
import sys
import tempfile
import shutil
from pathlib import Path

# Setup environment before importing site_api
tmp_dir = tempfile.mkdtemp()
os.environ["STUDIO_SITES"] = tmp_dir

from fastapi import FastAPI
from fastapi.testclient import TestClient
import site_api

app = FastAPI()
app.include_router(site_api.router)
client = TestClient(app)

# Mock build_site
def mock_build_site(brief, out_dir, runner=None, **kw):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text("<html><body>Test</body></html>")
    (out / "styles.css").write_text("body { color: red; }")
    return {"files": ["index.html", "styles.css"], "problems": []}

site_api.build_site = mock_build_site

# Test 1: Build success
resp = client.post("/api/site/build", json={"brief": {"name": "Test Site"}})
assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
data = resp.json()
assert "site_id" in data
assert len(data["site_id"]) == 12
assert data["files"] == ["index.html", "styles.css"]
assert data["problems"] == []
site_id = data["site_id"]

# Test 2: Bad brief 400
resp = client.post("/api/site/build", json={"brief": {}})
assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
assert "problems" in resp.json()

# Test 3: File serving
resp = client.get(f"/api/site/{site_id}/index.html")
assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
assert resp.text == "<html><body>Test</body></html>"
# Check that content-type starts with text/html
assert resp.headers["content-type"].startswith("text/html"), f"Expected text/html, got {resp.headers['content-type']}"

resp = client.get(f"/api/site/{site_id}/styles.css")
assert resp.status_code == 200
assert resp.headers["content-type"].startswith("text/css"), f"Expected text/css, got {resp.headers['content-type']}"

# Test 4: Traversal attempts
resp = client.get(f"/api/site/{site_id}/..%2f..%2fetc%2fpasswd")
assert resp.status_code == 404, f"Expected 404 for traversal, got {resp.status_code}"

resp = client.get(f"/api/site/{site_id}/../secret.txt")
assert resp.status_code == 404, f"Expected 404 for traversal, got {resp.status_code}"

resp = client.get(f"/api/site/{site_id}/%2Fetc%2Fpasswd")
assert resp.status_code == 404, f"Expected 404 for absolute path, got {resp.status_code}"

# Test 5: Invalid site id
resp = client.get("/api/site/invalid_id/index.html")
assert resp.status_code == 404, f"Expected 404 for invalid id, got {resp.status_code}"

resp = client.get("/api/site/ABCDEF123456/index.html")
assert resp.status_code == 404, f"Expected 404 for uppercase id, got {resp.status_code}"

# Test 6: Non-existent file
resp = client.get(f"/api/site/{site_id}/nonexistent.html")
assert resp.status_code == 404, f"Expected 404 for non-existent file, got {resp.status_code}"

# Test 7: List files
resp = client.get(f"/api/site/{site_id}")
assert resp.status_code == 200
files = resp.json()["files"]
assert "index.html" in files
assert "styles.css" in files

# Cleanup
shutil.rmtree(tmp_dir, ignore_errors=True)

print('ok')
