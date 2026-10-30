import torch

from n_4_real_time_touchdesigner_visuals import (
    PSN_TD_FrameEncode,
    PSN_TD_Control_Parse,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    encode_frame,
    decode_frame,
    parse_control_message,
)


def test_module_mappings():
    assert "PSN_TD_FrameEncode" in NODE_CLASS_MAPPINGS
    assert "PSN_TD_Control_Parse" in NODE_CLASS_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_TD_FrameEncode"]
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_TD_Control_Parse"]


def test_input_types_shape():
    it = PSN_TD_FrameEncode.INPUT_TYPES()
    assert "image" in it["required"]
    assert it["required"]["image"] == ("IMAGE",)
    assert PSN_TD_FrameEncode.FUNCTION == "run"
    assert PSN_TD_FrameEncode.CATEGORY.startswith("ParametricStudio/")
    assert PSN_TD_FrameEncode.RETURN_TYPES == ("BOOLEAN", "INT", "STRING")

    it2 = PSN_TD_Control_Parse.INPUT_TYPES()
    assert "message" in it2["required"]
    assert PSN_TD_Control_Parse.RETURN_TYPES == ("STRING", "FLOAT")


def test_encode_roundtrip_4ch():
    img = torch.rand(2, 8, 8, 4)
    payload, meta = encode_frame(img, channel="video_in")
    assert meta["B"] == 2 and meta["H"] == 8 and meta["W"] == 8 and meta["C"] == 4
    assert meta["raw_bytes"] == 2 * 8 * 8 * 4
    assert meta["total_bytes"] == 24 + meta["raw_bytes"]
    x2, m2 = decode_frame(payload)
    assert x2.shape == (2, 8, 8, 4)
    assert m2["channel"] == "vide"  # channel is truncated to 4 bytes in the header
    # uint8 quantization: max abs error <= 1/255
    assert (x2 - img).abs().max().item() <= 1.0 / 255.0 + 1e-6


def test_encode_roundtrip_3ch_and_clamp():
    img = torch.rand(1, 4, 6, 3)
    # push some values out of range to test clamping
    img[0, 0, 0, 0] = 5.0
    img[0, 0, 1, 1] = -3.0
    payload, meta = encode_frame(img, channel="abc")
    x2, _ = decode_frame(payload)
    assert x2.shape == (1, 4, 6, 3)
    assert x2.min().item() >= 0.0
    assert x2.max().item() <= 1.0
    # clamped values should be exactly 0 or 1 (within quantization)
    assert abs(x2[0, 0, 0, 0].item() - 1.0) <= 1.0 / 255.0 + 1e-6
    assert abs(x2[0, 0, 1, 1].item() - 0.0) <= 1.0 / 255.0 + 1e-6


def test_encode_does_not_mutate_input():
    img = torch.rand(1, 4, 4, 4)
    snapshot = img.clone()
    encode_frame(img, channel="x")
    assert torch.equal(img, snapshot)


def test_encode_bad_dims():
    bad = torch.rand(4, 4, 4)  # 3 dims
    try:
        encode_frame(bad)
        raise AssertionError("expected ValueError for 3-dim input")
    except ValueError:
        pass


def test_encode_bad_channels():
    bad = torch.rand(1, 4, 4, 2)  # 2 channels not allowed
    try:
        encode_frame(bad)
        raise AssertionError("expected ValueError for 2 channels")
    except ValueError:
        pass


def test_encode_bad_type():
    try:
        encode_frame("not a tensor")
        raise AssertionError("expected TypeError")
    except TypeError:
        pass


def test_decode_bad_magic():
    try:
        decode_frame(b"XXXX" + b"\x00" * 20)
        raise AssertionError("expected ValueError for bad magic")
    except ValueError:
        pass


def test_decode_too_short():
    try:
        decode_frame(b"PSNTD1")
        raise AssertionError("expected ValueError for short payload")
    except ValueError:
        pass


def test_node_run_encode():
    node = PSN_TD_FrameEncode()
    img = torch.rand(1, 16, 16, 4)
    sent, nbytes, ch = node.run(img, channel="video_in", protocol="osc")
    assert sent is True
    assert nbytes == 24 + 1 * 16 * 16 * 4
    assert ch == "vide"  # channel truncated to 4 bytes


def test_node_run_encode_bad_protocol():
    node = PSN_TD_FrameEncode()
    img = torch.rand(1, 4, 4, 4)
    try:
        node.run(img, channel="x", protocol="http")
        raise AssertionError("expected ValueError for bad protocol")
    except ValueError:
        pass


def test_parse_control_basic():
    cmd, val = parse_control_message("/control/stop")
    assert cmd == "stop"
    assert val == 0.0


def test_parse_control_with_value():
    cmd, val = parse_control_message("/control/mode 2.5")
    assert cmd == "mode"
    assert abs(val - 2.5) < 1e-9


def test_parse_control_negative_and_extra():
    cmd, val = parse_control_message("/control/offset -1.25 extra junk")
    assert cmd == "offset"
    assert abs(val - (-1.25)) < 1e-9


def test_parse_control_bad_path():
    try:
        parse_control_message("/other/stop")
        raise AssertionError("expected ValueError for non-control path")
    except ValueError:
        pass


def test_parse_control_no_slash():
    try:
        parse_control_message("control/stop")
        raise AssertionError("expected ValueError for missing leading slash")
    except ValueError:
        pass


def test_parse_control_bad_value():
    try:
        parse_control_message("/control/stop abc")
        raise AssertionError("expected ValueError for non-numeric value")
    except ValueError:
        pass


def test_parse_control_bad_type():
    try:
        parse_control_message(12345)
        raise AssertionError("expected TypeError")
    except TypeError:
        pass


def test_node_run_parse():
    node = PSN_TD_Control_Parse()
    cmd, val = node.run("/control/pause 1.0")
    assert cmd == "pause"
    assert abs(val - 1.0) < 1e-9


def main():
    test_module_mappings()
    test_input_types_shape()
    test_encode_roundtrip_4ch()
    test_encode_roundtrip_3ch_and_clamp()
    test_encode_does_not_mutate_input()
    test_encode_bad_dims()
    test_encode_bad_channels()
    test_encode_bad_type()
    test_decode_bad_magic()
    test_decode_too_short()
    test_node_run_encode()
    test_node_run_encode_bad_protocol()
    test_parse_control_basic()
    test_parse_control_with_value()
    test_parse_control_negative_and_extra()
    test_parse_control_bad_path()
    test_parse_control_no_slash()
    test_parse_control_bad_value()
    test_parse_control_bad_type()
    test_node_run_parse()
    print("ok")


if __name__ == "__main__":
    main()
