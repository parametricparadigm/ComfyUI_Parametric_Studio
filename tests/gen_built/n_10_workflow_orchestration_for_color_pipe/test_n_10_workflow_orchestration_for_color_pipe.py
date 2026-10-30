import json
import torch

from n_10_workflow_orchestration_for_color_pipe import (
    PSN_WorkflowOrchestrator,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def make_img(b=1, h=4, w=4, c=3, val=0.5):
    return torch.full((b, h, w, c), val, dtype=torch.float32)


def wf(nodes):
    return json.dumps({"nodes": nodes})


def test_module_mappings():
    assert "PSN_WorkflowOrchestrator" in NODE_CLASS_MAPPINGS
    assert "PSN_WorkflowOrchestrator" in NODE_DISPLAY_NAME_MAPPINGS
    cls = PSN_WorkflowOrchestrator
    assert cls.FUNCTION == "run"
    assert cls.RETURN_TYPES == ("IMAGE", "STRING")
    assert cls.RETURN_NAMES == ("image", "log_json")
    it = cls.INPUT_TYPES()
    assert "image" in it["required"] and "workflow_json" in it["required"]


def test_exposure_contrast_applied():
    node = PSN_WorkflowOrchestrator()
    img = make_img(val=0.5)
    w = wf([
        {"op": "exposure", "params": {"ev": 1.0}, "name": "exp"},
        {"op": "contrast", "params": {"amount": 2.0}, "name": "con"},
    ])
    out, log_json = node.run(img, w)
    log = json.loads(log_json)
    assert len(log) == 2
    assert log[0]["op"] == "exposure" and log[1]["op"] == "contrast"
    x = torch.clamp(img * 2.0, 0, 1)
    expected = torch.clamp(0.5 + (x - 0.5) * 2.0, 0, 1)
    assert torch.allclose(out, expected, atol=1e-6)
    assert torch.allclose(img, torch.full_like(img, 0.5))


def test_bad_json_raises():
    node = PSN_WorkflowOrchestrator()
    try:
        node.run(make_img(), "{not json")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_unknown_op_raises():
    node = PSN_WorkflowOrchestrator()
    try:
        node.run(make_img(), wf([{"op": "nope", "params": {}}]))
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_cycle_forward_ref_raises():
    node = PSN_WorkflowOrchestrator()
    w = wf([
        {"op": "exposure", "params": {}, "name": "a", "depends_on": ["b"]},
        {"op": "exposure", "params": {}, "name": "b"},
    ])
    try:
        node.run(make_img(), w)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_empty_workflow_raises():
    node = PSN_WorkflowOrchestrator()
    try:
        node.run(make_img(), wf([]))
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_bad_image_raises():
    node = PSN_WorkflowOrchestrator()
    try:
        node.run(torch.zeros(4, 4), wf([{"op": "exposure", "params": {}}]))
        assert False, "expected error"
    except (TypeError, ValueError):
        pass


def test_multi_node_pipeline_and_log():
    node = PSN_WorkflowOrchestrator()
    img = make_img(val=0.25)
    w = wf([
        {"op": "exposure", "params": {"ev": 1.0}, "name": "e"},
        {"op": "brightness", "params": {"delta": 0.1}, "name": "b"},
        {"op": "gamma", "params": {"gamma": 2.0}, "name": "g"},
        {"op": "saturation", "params": {"amount": 1.5}, "name": "s"},
        {"op": "levels", "params": {"in_lo": 0.0, "in_hi": 1.0}, "name": "l"},
    ])
    out, log_json = node.run(img, w)
    log = json.loads(log_json)
    assert len(log) == 5
    assert [e["op"] for e in log] == ["exposure", "brightness", "gamma", "saturation", "levels"]
    assert out.shape == img.shape
    assert out.min() >= 0.0 and out.max() <= 1.0
    x = torch.clamp(img * 2.0, 0, 1)
    x = torch.clamp(x + 0.1, 0, 1)
    x = torch.clamp(torch.pow(x.clamp(min=1e-6), 0.5), 0, 1)
    gray = x.mean(dim=-1, keepdim=True)
    x = torch.clamp(x + (x - gray) * 0.5, 0, 1)
    x = torch.clamp((x - 0.0) / 1.0, 0, 1)
    assert torch.allclose(out, x, atol=1e-5)


def test_alpha_channel_preserved():
    node = PSN_WorkflowOrchestrator()
    img = torch.zeros(1, 2, 2, 4)
    img[..., :3] = 0.5
    img[..., 3] = 0.7
    w = wf([{"op": "tint", "params": {"r": 0.1, "g": 0.0, "b": -0.1}}])
    out, _ = node.run(img, w)
    assert out.shape[-1] == 4
    assert torch.allclose(out[..., 3], torch.full((1, 2, 2), 0.7))
    assert torch.allclose(out[..., 0], torch.full((1, 2, 2), 0.6))
    assert torch.allclose(out[..., 2], torch.full((1, 2, 2), 0.4))


if __name__ == "__main__":
    test_module_mappings()
    test_exposure_contrast_applied()
    test_bad_json_raises()
    test_unknown_op_raises()
    test_cycle_forward_ref_raises()
    test_empty_workflow_raises()
    test_bad_image_raises()
    test_multi_node_pipeline_and_log()
    test_alpha_channel_preserved()
    print("ok")
