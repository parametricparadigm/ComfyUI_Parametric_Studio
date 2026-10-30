"""Tests for n_5_dynamic_pipeline_routing.PSN_Request_Router.

Run with:  python3 -B test_n_5_dynamic_pipeline_routing.py
Prints 'ok' and exits 0 on success.
"""

import n_5_dynamic_pipeline_routing as mod


def _router():
    return mod.PSN_Request_Router()


def test_module_mappings():
    """Module-level mappings exist and reference the class."""
    assert "PSN_Request_Router" in mod.NODE_CLASS_MAPPINGS
    assert mod.NODE_CLASS_MAPPINGS["PSN_Request_Router"] is mod.PSN_Request_Router
    assert "PSN_Request_Router" in mod.NODE_DISPLAY_NAME_MAPPINGS
    assert isinstance(mod.NODE_DISPLAY_NAME_MAPPINGS["PSN_Request_Router"], str)


def test_input_types_schema():
    """INPUT_TYPES returns the expected keys and types."""
    spec = mod.PSN_Request_Router.INPUT_TYPES()
    assert "required" in spec
    assert "request_type" in spec["required"]
    assert "payload" in spec["required"]
    # request_type must be a STRING widget
    assert spec["required"]["request_type"][0] == "STRING"
    # payload must be ANY
    assert spec["required"]["payload"][0] == "ANY"
    # optional default_route must be present
    assert "optional" in spec
    assert "default_route" in spec["optional"]


def test_return_signature():
    """RETURN_TYPES / RETURN_NAMES / FUNCTION / CATEGORY are correct."""
    assert mod.PSN_Request_Router.RETURN_TYPES == ("ANY", "ANY", "ANY", "STRING")
    assert mod.PSN_Request_Router.RETURN_NAMES == (
        "video_payload",
        "music_payload",
        "image_payload",
        "routed_to",
    )
    assert mod.PSN_Request_Router.FUNCTION == "run"
    assert mod.PSN_Request_Router.CATEGORY.startswith("ParametricStudio/")


def test_route_video():
    """request_type='video' puts the payload on the video output only."""
    r = _router()
    payload = {"frames": 120, "codec": "h264"}
    v, m, i, routed = r.run("video", payload)
    assert v is payload          # same object, not a copy
    assert m is None
    assert i is None
    assert routed == "video"


def test_route_music():
    r = _router()
    payload = [1, 2, 3]
    v, m, i, routed = r.run("music", payload)
    assert v is None
    assert m is payload
    assert i is None
    assert routed == "music"


def test_route_image():
    r = _router()
    payload = "img.png"
    v, m, i, routed = r.run("image", payload)
    assert v is None
    assert m is None
    assert i is payload
    assert routed == "image"


def test_case_and_whitespace_insensitive():
    """'  VIDEO  ' and 'Music' should still route correctly."""
    r = _router()
    p = "x"
    v, m, i, routed = r.run("  VIDEO  ", p)
    assert v is p and routed == "video"
    v, m, i, routed = r.run("Music", p)
    assert m is p and routed == "music"


def test_unknown_type_defaults_to_none():
    """Misspelled / unknown type with default_route='none' -> all None."""
    r = _router()
    p = "data"
    v, m, i, routed = r.run("vidoe", p)   # misspelled
    assert v is None and m is None and i is None
    assert routed == "none"


def test_unknown_type_with_default_route():
    """Unknown type falls back to the configured default lane."""
    r = _router()
    p = "data"
    v, m, i, routed = r.run("audio", p, default_route="music")
    assert m is p and routed == "music"
    assert v is None and i is None


def test_bad_input_non_string_request_type():
    """A non-string request_type must not raise; it routes to default."""
    r = _router()
    p = 42
    v, m, i, routed = r.run(12345, p)          # int, not str
    assert routed == "none"
    assert v is None and m is None and i is None

    # With a default route it should land there.
    v, m, i, routed = r.run(None, p, default_route="image")
    assert i is p and routed == "image"


def test_payload_not_mutated():
    """The payload object must be returned unchanged (identity + content)."""
    r = _router()
    payload = {"a": [1, 2, 3]}
    v, m, i, routed = r.run("video", payload)
    assert v is payload
    assert payload == {"a": [1, 2, 3]}


def test_none_payload():
    """A None payload is valid and routes normally."""
    r = _router()
    v, m, i, routed = r.run("music", None)
    assert m is None   # payload was None, so output is None
    assert routed == "music"
    assert v is None and i is None


def test_default_route_none_string():
    """default_route='none' (the string) is handled, not treated as a lane."""
    r = _router()
    p = "x"
    v, m, i, routed = r.run("bogus", p, default_route="none")
    assert routed == "none"
    assert v is None and m is None and i is None


if __name__ == "__main__":
    test_module_mappings()
    test_input_types_schema()
    test_return_signature()
    test_route_video()
    test_route_music()
    test_route_image()
    test_case_and_whitespace_insensitive()
    test_unknown_type_defaults_to_none()
    test_unknown_type_with_default_route()
    test_bad_input_non_string_request_type()
    test_payload_not_mutated()
    test_none_payload()
    test_default_route_none_string()
    print("ok")
