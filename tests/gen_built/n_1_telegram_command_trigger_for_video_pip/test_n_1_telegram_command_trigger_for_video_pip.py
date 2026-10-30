"""Tests for n_1_telegram_command_trigger_for_video_pip.

Run with:  python3 -B test_n_1_telegram_command_trigger_for_video_pip.py
Must print 'ok' and exit 0.
"""

import base64
import json

import torch

import n_1_telegram_command_trigger_for_video_pip as mod


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_b64_image(h, w, value=128):
    """Build the raw container used by the module and base64-encode it."""
    header = h.to_bytes(4, "big") + w.to_bytes(4, "big")
    data = bytes([value]) * (h * w * 3)
    return base64.b64encode(header + data).decode("ascii")


def _make_update(cid, text=None, photo_b64=None):
    msg = {
        "chat": {"id": cid},
        "from": {"id": cid},
    }
    if text is not None:
        msg["text"] = text
    if photo_b64 is not None:
        msg["photo_b64"] = photo_b64
    return {"update_id": 1, "message": msg}


# ---------------------------------------------------------------------------
# 1. module-level registration
# ---------------------------------------------------------------------------

def test_registration():
    assert "PSN_Telegram_Command_Parser" in mod.NODE_CLASS_MAPPINGS
    assert "PSN_Telegram_Sender_Prep" in mod.NODE_CLASS_MAPPINGS
    assert mod.NODE_DISPLAY_NAME_MAPPINGS["PSN_Telegram_Command_Parser"]
    # INPUT_TYPES must be a classmethod returning a dict with 'required'
    it = mod.PSN_Telegram_Command_Parser.INPUT_TYPES()
    assert "required" in it
    assert "updates_json" in it["required"]
    it2 = mod.PSN_Telegram_Sender_Prep.INPUT_TYPES()
    assert "media" in it2["required"]
    # FUNCTION and CATEGORY
    assert mod.PSN_Telegram_Command_Parser.FUNCTION == "run"
    assert mod.PSN_Telegram_Command_Parser.CATEGORY.startswith("ParametricStudio/")
    assert mod.PSN_Telegram_Sender_Prep.FUNCTION == "run"


# ---------------------------------------------------------------------------
# 2. parser: plain text message, no allow-list
# ---------------------------------------------------------------------------

def test_parser_plain_text():
    node = mod.PSN_Telegram_Command_Parser()
    payload = json.dumps([_make_update(42, text="hello world")])
    chat_id, text, img, is_cmd = node.run(payload, allowed_chat_ids="", command_prefix="/")
    assert chat_id == 42
    assert text == "hello world"
    assert is_cmd is False
    assert isinstance(img, torch.Tensor)
    assert img.shape == (1, 1, 1, 3)  # default empty image


# ---------------------------------------------------------------------------
# 3. parser: command prefix detection
# ---------------------------------------------------------------------------

def test_parser_command_prefix():
    node = mod.PSN_Telegram_Command_Parser()
    payload = json.dumps([_make_update(7, text="/generate a cat")])
    chat_id, text, img, is_cmd = node.run(payload, allowed_chat_ids="", command_prefix="/")
    assert chat_id == 7
    assert is_cmd is True
    assert text.startswith("/")


# ---------------------------------------------------------------------------
# 4. parser: allow-list security (disallowed chat is ignored)
# ---------------------------------------------------------------------------

def test_parser_allowlist_blocks():
    node = mod.PSN_Telegram_Command_Parser()
    payload = json.dumps([_make_update(999, text="secret")])
    chat_id, text, img, is_cmd = node.run(payload, allowed_chat_ids="1,2,3", command_prefix="/")
    # chat 999 is not in the allow-list -> no message accepted
    assert chat_id == 0
    assert text == ""


def test_parser_allowlist_allows():
    node = mod.PSN_Telegram_Command_Parser()
    payload = json.dumps([_make_update(2, text="ok")])
    chat_id, text, img, is_cmd = node.run(payload, allowed_chat_ids="1, 2 ,3", command_prefix="/")
    assert chat_id == 2
    assert text == "ok"


# ---------------------------------------------------------------------------
# 5. parser: image attachment decoded to tensor
# ---------------------------------------------------------------------------

def test_parser_image_decode():
    node = mod.PSN_Telegram_Command_Parser()
    b64 = _make_b64_image(4, 5, value=200)
    payload = json.dumps([_make_update(10, text="with image", photo_b64=b64)])
    chat_id, text, img, is_cmd = node.run(payload, allowed_chat_ids="", command_prefix="/")
    assert chat_id == 10
    assert img.shape == (1, 4, 5, 3)
    assert img.dtype == torch.float32
    # value 200/255
    expected = 200.0 / 255.0
    assert torch.allclose(img, torch.full((1, 4, 5, 3), expected), atol=1e-5)


# ---------------------------------------------------------------------------
# 6. parser: bad JSON input does not crash
# ---------------------------------------------------------------------------

def test_parser_bad_json():
    node = mod.PSN_Telegram_Command_Parser()
    chat_id, text, img, is_cmd = node.run("not valid json{{{", allowed_chat_ids="", command_prefix="/")
    assert chat_id == 0
    assert text == ""
    assert is_cmd is False
    assert img.shape == (1, 1, 1, 3)


# ---------------------------------------------------------------------------
# 7. parser: empty payload
# ---------------------------------------------------------------------------

def test_parser_empty():
    node = mod.PSN_Telegram_Command_Parser()
    chat_id, text, img, is_cmd = node.run("[]", allowed_chat_ids="", command_prefix="/")
    assert chat_id == 0
    assert text == ""
    assert is_cmd is False


# ---------------------------------------------------------------------------
# 8. sender prep: valid image tensor
# ---------------------------------------------------------------------------

def test_sender_prep_image():
    node = mod.PSN_Telegram_Sender_Prep()
    img = torch.rand(1, 8, 8, 3)  # [B, H, W, C]
    ready, nbytes, endpoint, body = node.run(img, chat_id=55, caption="hi", media_type="image")
    assert ready is True
    assert nbytes > 0
    assert endpoint == "sendPhoto"
    parsed = json.loads(body)
    assert parsed["chat_id"] == 55
    assert parsed["caption"] == "hi"
    assert parsed["media_type"] == "image"
    assert "media_b64" in parsed


# ---------------------------------------------------------------------------
# 9. sender prep: video endpoint
# ---------------------------------------------------------------------------

def test_sender_prep_video():
    node = mod.PSN_Telegram_Sender_Prep()
    img = torch.rand(1, 4, 4, 3)
    ready, nbytes, endpoint, body = node.run(img, chat_id=1, caption="", media_type="video")
    assert ready is True
    assert endpoint == "sendVideo"


# ---------------------------------------------------------------------------
# 10. sender prep: bad input (non-tensor)
# ---------------------------------------------------------------------------

def test_sender_prep_bad_input():
    node = mod.PSN_Telegram_Sender_Prep()
    ready, nbytes, endpoint, body = node.run("not a tensor", chat_id=1, caption="", media_type="image")
    assert ready is False
    assert nbytes == 0
    assert endpoint == ""
    assert body == ""


# ---------------------------------------------------------------------------
# 11. sender prep: bad media_type
# ---------------------------------------------------------------------------

def test_sender_prep_bad_media_type():
    node = mod.PSN_Telegram_Sender_Prep()
    img = torch.rand(1, 2, 2, 3)
    ready, nbytes, endpoint, body = node.run(img, chat_id=1, caption="", media_type="audio")
    assert ready is False


# ---------------------------------------------------------------------------
# 12. round-trip: tensor -> b64 -> tensor
# ---------------------------------------------------------------------------

def test_roundtrip():
    img = torch.rand(6, 7, 3)
    b64 = mod._tensor_to_b64(img)
    back = mod._b64_to_tensor(b64)
    assert back.shape == (6, 7, 3)
    assert torch.allclose(img, back, atol=1.0 / 255.0 + 1e-5)


# ---------------------------------------------------------------------------
# 13. sender prep: 3D tensor (no batch dim)
# ---------------------------------------------------------------------------

def test_sender_prep_3d():
    node = mod.PSN_Telegram_Sender_Prep()
    img = torch.rand(3, 3, 3)
    ready, nbytes, endpoint, body = node.run(img, chat_id=9, caption="c", media_type="document")
    assert ready is True
    assert endpoint == "sendDocument"


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    test_registration()
    test_parser_plain_text()
    test_parser_command_prefix()
    test_parser_allowlist_blocks()
    test_parser_allowlist_allows()
    test_parser_image_decode()
    test_parser_bad_json()
    test_parser_empty()
    test_sender_prep_image()
    test_sender_prep_video()
    test_sender_prep_bad_input()
    test_sender_prep_bad_media_type()
    test_roundtrip()
    test_sender_prep_3d()
    print("ok")


if __name__ == "__main__":
    main()
