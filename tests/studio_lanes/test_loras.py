import os
import sys
import tempfile
import shutil
import time
from fastapi.testclient import TestClient
from loras import router, _cache

# Create a temporary directory structure
tmp_dir = tempfile.mkdtemp()
models_root = os.path.join(tmp_dir, "models")
loras_dir = os.path.join(models_root, "loras")
os.makedirs(loras_dir, exist_ok=True)

# Create some test files
# 1. SFW LoRA
with open(os.path.join(loras_dir, "flux_style.safetensors"), "w") as f:
    f.write("x" * 1024) # 1KB

# 2. NSFW LoRA (should be filtered)
with open(os.path.join(loras_dir, "nsfw_test.safetensors"), "w") as f:
    f.write("x" * 1024)

# 3. Nested SFW LoRA
nested_dir = os.path.join(loras_dir, "nested")
os.makedirs(nested_dir, exist_ok=True)
with open(os.path.join(nested_dir, "h3_character.safetensors"), "w") as f:
    f.write("x" * 2048) # 2KB

# 4. Non-safetensors file (should be ignored)
with open(os.path.join(loras_dir, "ignore_me.txt"), "w") as f:
    f.write("x" * 1024)

# 5. Symlink pointing outside (should be ignored)
outside_dir = os.path.join(tmp_dir, "outside")
os.makedirs(outside_dir, exist_ok=True)
outside_file = os.path.join(outside_dir, "outside.safetensors")
with open(outside_file, "w") as f:
    f.write("x" * 1024)
    
symlink_path = os.path.join(loras_dir, "symlink.safetensors")
if os.path.exists(symlink_path):
    os.remove(symlink_path)
os.symlink(outside_file, symlink_path)

# 6. Music3 LoRA
music_dir = os.path.join(loras_dir, "music3")
os.makedirs(music_dir, exist_ok=True)
with open(os.path.join(music_dir, "jazz.safetensors"), "w") as f:
    f.write("x" * 1024)

# Set env var
os.environ["STUDIO_MODELS_ROOT"] = models_root

# Clear cache
_cache["data"] = None
_cache["timestamp"] = 0

# Create app
from fastapi import FastAPI
app = FastAPI()
app.include_router(router)
client = TestClient(app)

# Test 1: Basic listing
response = client.get("/api/loras")
assert response.status_code == 200
data = response.json()

# Expected items:
# - flux_style.safetensors (Family: FLUX, Kind: style)
# - nested/h3_character.safetensors (Family: MiniMax H3, Kind: character)
# - music3/jazz.safetensors (Family: MiniMax Music 3, Kind: music)
# nsfw_test.safetensors should be excluded
# ignore_me.txt should be excluded
# symlink.safetensors should be excluded

names = [item["name"] for item in data["items"]]
assert "flux_style.safetensors" in names, f"flux_style not found in {names}"
assert "nested/h3_character.safetensors" in names, f"h3_character not found in {names}"
assert "music3/jazz.safetensors" in names, f"jazz not found in {names}"
assert "nsfw_test.safetensors" not in names, "nsfw_test should be filtered"
assert "ignore_me.txt" not in names, "txt file should be ignored"
assert "symlink.safetensors" not in names, "symlink should be ignored"

# Check families
assert data["families"].get("FLUX") == 1
assert data["families"].get("MiniMax H3") == 1
assert data["families"].get("MiniMax Music 3") == 1

# Check kinds
assert data["kinds"].get("style") == 1
assert data["kinds"].get("character") == 1
assert data["kinds"].get("music") == 1

# Test 2: Search
response = client.get("/api/loras?q=flux")
data = response.json()
names = [item["name"] for item in data["items"]]
assert "flux_style.safetensors" in names
assert "nested/h3_character.safetensors" not in names

# Test 3: Filter by family
response = client.get("/api/loras?family=FLUX")
data = response.json()
names = [item["name"] for item in data["items"]]
assert "flux_style.safetensors" in names
assert "nested/h3_character.safetensors" not in names

# Test 4: Filter by kind
response = client.get("/api/loras?kind=music")
data = response.json()
names = [item["name"] for item in data["items"]]
assert "music3/jazz.safetensors" in names
assert "flux_style.safetensors" not in names

# Cleanup
shutil.rmtree(tmp_dir)

print('ok')
