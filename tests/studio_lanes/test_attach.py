import json
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Setup environment for tests
tmp_dir = tempfile.mkdtemp()
os.environ["STUDIO_CONFIG_DIR"] = tmp_dir

# Import module
sys.path.insert(0, os.getcwd())
import attach

def test_validation():
    # Test URL validation
    try:
        attach.save(comfy_url="ftp://localhost")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
        
    try:
        attach.save(comfy_url="http://example.com")
        assert False, "Should have raised ValueError for public host"
    except ValueError:
        pass
        
    # Test valid loopback
    attach.save(comfy_url="http://localhost:8188")
    settings = attach.load()
    assert settings["comfy_url"] == "http://localhost:8188"
    
    # Test workflows_dir validation
    try:
        attach.save(workflows_dir="/nonexistent/dir")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
        
    valid_dir = tempfile.mkdtemp()
    attach.save(workflows_dir=valid_dir)
    settings = attach.load()
    assert settings["workflows_dir"] == str(Path(valid_dir).resolve())

def test_sfw():
    wf = {
        "nodes": [
            {"title": "Safe", "type": "KSampler", "widgets_values": ["hello"]},
            {"title": "Bad", "type": "NSFWNode", "widgets_values": ["nude"]}
        ]
    }
    problems = attach.sfw_problems(wf)
    assert len(problems) > 0
    assert "nsfw" in problems[0].lower()
    assert "nude" in problems[0].lower()
    
    wf_safe = {
        "nodes": [
            {"title": "Safe", "type": "KSampler", "widgets_values": ["hello", "essex"]}
        ]
    }
    problems = attach.sfw_problems(wf_safe)
    assert len(problems) == 0

def test_scan():
    dir_path = tempfile.mkdtemp()
    
    # Create a valid workflow
    wf1 = {"nodes": [{"id": 1, "title": "A", "type": "KSampler", "widgets_values": []}]}
    with open(os.path.join(dir_path, "wf1.json"), "w") as f:
        json.dump(wf1, f)
        
    # Create an NSFW workflow
    wf2 = {"nodes": [{"id": 1, "title": "B", "type": "KSampler", "widgets_values": ["porn"]}]}
    with open(os.path.join(dir_path, "wf2.json"), "w") as f:
        json.dump(wf2, f)
        
    results = attach.scan_workflows(dir_path)
    assert len(results) == 2
    
    r1 = next(r for r in results if r["file"] == "wf1.json")
    assert r1["sfw"] == True
    assert r1["nodes"] == 1
    
    r2 = next(r for r in results if r["file"] == "wf2.json")
    assert r2["sfw"] == False
    assert len(r2["problems"]) > 0

def test_to_app():
    wf = {
        "nodes": [
            {"id": 1, "title": "A", "type": "KSampler", "widgets_values": []},
            {"id": 2, "title": "B", "type": "VAEDecode", "widgets_values": []}
        ]
    }
    inputs = [[1, "seed"]]
    outputs = [2]
    
    app = attach.to_app(wf, inputs, outputs)
    assert app["extra"]["linearMode"] == True
    assert app["extra"]["linearData"]["inputs"] == inputs
    assert app["extra"]["linearData"]["outputs"] == outputs
    
    # Test validation error
    try:
        attach.to_app(wf, [[99, "seed"]], [2])
        assert False, "Should have raised ValueError"
    except ValueError:
        pass

def test_import():
    dir_path = tempfile.mkdtemp()
    dest_dir = tempfile.mkdtemp()
    
    # Create NSFW workflow
    wf = {"nodes": [{"id": 1, "title": "A", "type": "KSampler", "widgets_values": ["sex"]}]}
    wf_file = os.path.join(dir_path, "bad.json")
    with open(wf_file, "w") as f:
        json.dump(wf, f)
        
    try:
        attach.import_workflow(wf_file, dest_dir, [[1, "seed"]], [1])
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "sex" in str(e)
        
    # Create Safe workflow
    wf_safe = {"nodes": [{"id": 1, "title": "A", "type": "KSampler", "widgets_values": ["safe"]}]}
    wf_safe_file = os.path.join(dir_path, "good.json")
    with open(wf_safe_file, "w") as f:
        json.dump(wf_safe, f)
        
    out_path = attach.import_workflow(wf_safe_file, dest_dir, [[1, "seed"]], [1])
    assert os.path.exists(out_path)
    assert out_path.endswith("good.app.json")

def test_router():
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(attach.router)
    client = TestClient(app)
    
    # Test GET
    r = client.get("/api/attach")
    assert r.status_code == 200
    
    # Test POST invalid
    r = client.post("/api/attach", json={"comfy_url": "http://example.com"})
    assert r.status_code == 400
    
    # Test POST valid
    r = client.post("/api/attach", json={"comfy_url": "http://localhost:8188"})
    assert r.status_code == 200
    
    # Test Test
    r = client.post("/api/attach/test", json={"url": "http://localhost:8188"})
    assert r.status_code == 200
    assert r.json()["ok"] == False # Connection refused expected

if __name__ == "__main__":
    test_validation()
    test_sfw()
    test_scan()
    test_to_app()
    test_import()
    test_router()
    print("ok")
