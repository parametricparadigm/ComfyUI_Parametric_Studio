"""Tests for psn_nodes.gen.psn_telegram_listener."""

import json
import pytest

from psn_nodes.gen.psn_telegram_listener import (
    PSN_Telegram_Listener,
    psn_redact_token,
    psn_parse_allow_list,
    psn_is_allowed,
    psn_is_command,
    psn_rate_limit_ok,
    psn_parse_updates_payload,
)


def test_psn_redact_token_normal():
    token = "1234567890:ABCDEFghijklMNOP"
    redacted = psn_redact_token(token)
    assert redacted.startswith("1234")
    assert redacted.endswith("MNOP")
    assert "*" in redacted
    assert "ABCDEF" not in redacted


def test_psn_redact_token_short():
    token = "ab"
    redacted = psn_redact_token(token)
    assert redacted == "ab"


def test_psn_parse_allow_list_valid():
    ids = psn_parse_allow_list("123, 456,789")
    assert ids == [123, 456, 789]


def test_psn_parse_allow_list_invalid():
    with pytest.raises(ValueError):
        psn_parse_allow_list("123, abc, 456")


def test_psn_is_command_variants():
    assert psn_is_command("/start") is True
    assert psn_is_command("!help") is True
    assert psn_is_command("hello") is False
    assert psn_is_command("") is False
    assert psn_is_command(None) is False


def test_psn_rate_limit_ok_valid():
    ok, why = psn_rate_limit_ok(5)
    assert ok is True
    assert why == "ok"


def test_psn_rate_limit_ok_too_small():
    ok, why = psn_rate_limit_ok(0)
    assert ok is False
    assert "must be >=" in why


def test_psn_rate_limit_ok_not_int():
    ok, why = psn_rate_limit_ok("5")
    assert ok is False


def test_psn_parse_updates_payload_with_message():
    payload = json.dumps({
        "ok": True,
        "result": [
            {
                "update_id": 1,
                "message": {
                    "message_id": 1,
                    "chat": {"id": 12345, "type": "private"},
                    "text": "/start",
                },
            }
        ],
    })
    parsed = psn_parse_updates_payload(payload)
    assert parsed["chat_id"] == 12345
    assert parsed["text_prompt"] == "/start"
    assert parsed["is_command"] is True
    assert parsed["has_image"] is False


def test_psn_parse_updates_payload_with_image():
    payload = json.dumps({
        "ok": True,
        "result": [
            {
                "update_id": 2,
                "message": {
                    "message_id": 2,
                    "chat": {"id": 67890, "type": "private"},
                    "photo": [{"file_id": "abc"}],
                    "caption": "a photo",
                },
            }
        ],
    })
    parsed = psn_parse_updates_payload(payload)
    assert parsed["chat_id"] == 67890
    assert parsed["has_image"] is True
    assert parsed["text_prompt"] == ""


def test_psn_parse_updates_payload_empty():
    parsed = psn_parse_updates_payload(json.dumps({"ok": True, "result": []}))
    assert parsed["chat_id"] == -1
    assert parsed["text_prompt"] == ""
    assert parsed["is_command"] is False


def test_psn_parse_updates_payload_invalid_json():
    with pytest.raises(ValueError):
        psn_parse_updates_payload("not json")


def test_psn_node_run_allowed_chat():
    node = PSN_Telegram_Listener()
    payload = json.dumps({
        "ok": True,
        "result": [
            {
                "update_id": 1,
                "message": {
                    "chat": {"id": 100},
                    "text": "hello",
                },
            }
        ],
    })
    chat_id, text, is_cmd, is_allowed, redacted = node.run(
        bot_token="1234567890:ABCDEFghijklMNOP",
        allowed_chat_ids="100,200",
        poll_interval=5,
        updates_payload=payload,
    )
    assert chat_id == 100
    assert text == "hello"
    assert is_cmd is False
    assert is_allowed is True
    assert redacted.startswith("1234")


def test_psn_node_run_disallowed_chat():
    node = PSN_Telegram_Listener()
    payload = json.dumps({
        "ok": True,
        "result": [
            {
                "update_id": 1,
                "message": {
                    "chat": {"id": 999},
                    "text": "hello",
                },
            }
        ],
    })
    chat_id, text, is_cmd, is_allowed, redacted = node.run(
        bot_token="1234567890:ABCDEFghijklMNOP",
        allowed_chat_ids="100,200",
        poll_interval=5,
        updates_payload=payload,
    )
    assert chat_id == 999
    assert is_allowed is False


def test_psn_node_run_bad_poll_interval():
    node = PSN_Telegram_Listener()
    payload = json.dumps({"ok": True, "result": []})
    with pytest.raises(ValueError):
        node.run(
            bot_token="tok",
            allowed_chat_ids="1",
            poll_interval=0,
            updates_payload=payload,
        )


def test_psn_node_run_bad_allow_list():
    node = PSN_Telegram_Listener()
    payload = json.dumps({"ok": True, "result": []})
    with pytest.raises(ValueError):
        node.run(
            bot_token="tok",
            allowed_chat_ids="1,abc",
            poll_interval=5,
            updates_payload=payload,
        )
