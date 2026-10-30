import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from presets import CAMERA, LOOKS, apply, router
from psn.camera import camera_moves
from fastapi.testclient import TestClient
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_camera_presets():
    assert len(CAMERA) == 8
    for key, val in CAMERA.items():
        assert 'label' in val
        assert 'phrase' in val
        assert 'blurb' in val
        moves = camera_moves(val['phrase'])
        assert moves == [key], f"Camera preset {key} phrase '{val['phrase']}' classified as {moves}"

def test_look_presets():
    assert len(LOOKS) == 24
    ids = set()
    for look in LOOKS:
        assert 'id' in look
        assert 'label' in look
        assert 'group' in look
        assert 'phrase' in look
        assert 'blurb' in look
        assert look['id'] not in ids, f"Duplicate look id: {look['id']}"
        ids.add(look['id'])
        moves = camera_moves(look['phrase'])
        assert moves == [], f"Look preset {look['id']} phrase '{look['phrase']}' contains camera moves: {moves}"

def test_apply_basic():
    # Video with camera and look
    result = apply("a cat", camera="push_in", look="noir", kind="video")
    assert isinstance(result, str)
    assert "a cat" in result
    assert "slow dolly push in toward the subject" in result
    assert "black and white, high contrast, dramatic shadows" in result
    # User text first
    assert result.startswith("a cat")

def test_apply_image_no_camera():
    # Image should not add camera
    result = apply("a dog", camera="pan", look="watercolor", kind="image")
    assert isinstance(result, str)
    assert "steady horizontal pan across the scene" not in result
    assert "soft watercolor painting, pastel colors, textured paper" in result

def test_apply_camera_conflict():
    # User prompt already has a camera move
    result = apply("pan across the room", camera="push_in", look="noir", kind="video")
    assert isinstance(result, tuple)
    text, notes = result
    assert "slow dolly push in toward the subject" not in text
    assert any("Camera move already present" in n for n in notes)

def test_apply_no_duplicates():
    # If prompt already contains the look phrase, it shouldn't be added again
    look_phrase = "black and white, high contrast, dramatic shadows"
    result = apply(look_phrase, look="noir", kind="image")
    assert isinstance(result, str)
    # Count occurrences
    assert result.count(look_phrase) == 1

def test_router_get():
    resp = client.get("/api/presets")
    assert resp.status_code == 200
    data = resp.json()
    assert "camera" in data
    assert "looks" in data
    assert len(data["camera"]) == 8
    assert len(data["looks"]) == 24

def test_router_apply():
    resp = client.post("/api/presets/apply", json={"prompt": "a city", "camera": "orbit", "look": "noir", "kind": "video"})
    assert resp.status_code == 200
    data = resp.json()
    assert "a city" in data["prompt"]
    assert "smooth orbit around the central figure" in data["prompt"]
    assert "black and white, high contrast, dramatic shadows" in data["prompt"]
    assert data["notes"] == []

def test_router_apply_conflict():
    resp = client.post("/api/presets/apply", json={"prompt": "pan the camera", "camera": "tilt", "kind": "video"})
    assert resp.status_code == 200
    data = resp.json()
    assert "gentle vertical tilt up from the base" not in data["prompt"]
    assert len(data["notes"]) > 0

if __name__ == "__main__":
    test_camera_presets()
    test_look_presets()
    test_apply_basic()
    test_apply_image_no_camera()
    test_apply_camera_conflict()
    test_apply_no_duplicates()
    test_router_get()
    test_router_apply()
    test_router_apply_conflict()
    print("ok")
