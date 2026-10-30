import json

import torch

from n_4_multi_stage_media_workbench import (
    PSN_AsTypeConverter,
    PSN_MediaStageOrchestrator,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def test_module_mappings():
    assert "PSN_MediaStageOrchestrator" in NODE_CLASS_MAPPINGS
    assert "PSN_AsTypeConverter" in NODE_CLASS_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_MediaStageOrchestrator"] == "Media Stage Orchestrator"
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_AsTypeConverter"] == "Asset Type Converter"
    # INPUT_TYPES classmethod exists and returns a dict with 'required'
    it = PSN_MediaStageOrchestrator.INPUT_TYPES()
    assert "required" in it
    assert "stage_config" in it["required"]
    it2 = PSN_AsTypeConverter.INPUT_TYPES()
    assert "required" in it2
    assert "target_type" in it2["required"]


def test_orchestrator_upscale_image():
    node = PSN_MediaStageOrchestrator()
    img = torch.rand(1, 8, 8, 3)
    cfg = json.dumps([{"name": "upscale", "params": {"factor": 2}}])
    out, log = node.run(cfg, img)
    assert out.shape == (1, 16, 16, 3)
    assert out.min() >= 0.0 and out.max() <= 1.0
    assert "upscale" in log
    assert "IMAGE -> IMAGE" in log
    # input not modified in place
    assert img.shape == (1, 8, 8, 3)


def test_orchestrator_multi_stage_order():
    node = PSN_MediaStageOrchestrator()
    img = torch.rand(1, 4, 4, 3)
    cfg = json.dumps([
        {"name": "color_grade", "params": {"brightness": 0.1, "contrast": 1.2}},
        {"name": "upscale", "params": {"factor": 2}},
        {"name": "normalize"},
    ])
    out, log = node.run(cfg, img)
    assert out.shape == (1, 8, 8, 3)
    lines = log.splitlines()
    assert len(lines) == 3
    assert lines[0].startswith("stage 0: color_grade")
    assert lines[1].startswith("stage 1: upscale")
    assert lines[2].startswith("stage 2: normalize")


def test_orchestrator_video_to_image_conversion():
    node = PSN_MediaStageOrchestrator()
    vid = torch.rand(1, 6, 4, 4, 3)
    cfg = json.dumps([{"name": "video_to_image"}])
    out, log = node.run(cfg, vid)
    assert out.shape == (1, 4, 4, 3)
    assert "VIDEO -> IMAGE" in log


def test_orchestrator_bad_inputs():
    node = PSN_MediaStageOrchestrator()
    img = torch.rand(1, 4, 4, 3)
    # invalid JSON
    try:
        node.run("{not json", img)
        assert False, "expected ValueError for bad JSON"
    except ValueError:
        pass
    # unknown stage name
    try:
        node.run(json.dumps([{"name": "nope"}]), img)
        assert False, "expected ValueError for unknown stage"
    except ValueError:
        pass
    # non-list config
    try:
        node.run(json.dumps({"name": "upscale"}), img)
        assert False, "expected ValueError for non-list config"
    except ValueError:
        pass
    # non-tensor asset
    try:
        node.run("[]", "not a tensor")
        assert False, "expected ValueError for non-tensor asset"
    except ValueError:
        pass


def test_converter_image_to_video():
    node = PSN_AsTypeConverter()
    img = torch.rand(2, 4, 4, 3)
    out = node.run(img, "VIDEO", frames=5)[0]
    assert out.shape == (2, 5, 4, 4, 3)
    # frames are identical copies of the image
    assert torch.equal(out[:, 0], img)
    assert torch.equal(out[:, 4], img)


def test_converter_video_to_image():
    node = PSN_AsTypeConverter()
    vid = torch.rand(1, 3, 4, 4, 3)
    out = node.run(vid, "IMAGE")[0]
    assert out.shape == (1, 4, 4, 3)
    assert torch.equal(out, vid[:, 0])


def test_converter_audio_roundtrip():
    node = PSN_AsTypeConverter()
    audio = torch.rand(1, 16)
    img = node.run(audio, "IMAGE")[0]
    assert img.shape == (1, 1, 16, 1)
    back = node.run(img, "AUDIO")[0]
    assert back.shape == (1, 16)
    assert torch.allclose(back, audio)


def test_converter_bad_target():
    node = PSN_AsTypeConverter()
    img = torch.rand(1, 4, 4, 3)
    try:
        node.run(img, "LASER")
        assert False, "expected ValueError for bad target_type"
    except ValueError:
        pass
    try:
        node.run("nope", "IMAGE")
        assert False, "expected ValueError for non-tensor input"
    except ValueError:
        pass


def test_audio_sync_stage():
    node = PSN_MediaStageOrchestrator()
    audio = torch.rand(1, 10)
    cfg = json.dumps([{"name": "audio_sync", "params": {"target_length": 20}}])
    out, log = node.run(cfg, audio)
    assert out.shape == (1, 20)
    assert "AUDIO -> AUDIO" in log


def main():
    test_module_mappings()
    test_orchestrator_upscale_image()
    test_orchestrator_multi_stage_order()
    test_orchestrator_video_to_image_conversion()
    test_orchestrator_bad_inputs()
    test_converter_image_to_video()
    test_converter_video_to_image()
    test_converter_audio_roundtrip()
    test_converter_bad_target()
    test_audio_sync_stage()
    print("ok")


if __name__ == "__main__":
    main()
