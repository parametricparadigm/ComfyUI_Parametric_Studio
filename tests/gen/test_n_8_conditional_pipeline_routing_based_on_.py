"""Tests for psn_nodes.gen.n_8_conditional_pipeline_routing_based_on_."""

import json

from psn_nodes.gen.n_8_conditional_pipeline_routing_based_on_ import (
    PSN_Type_Inspector,
    PSN_Pipeline_Router,
    psn_inspect_type,
    psn_validate_route_map,
    psn_route,
    TYPE_IMAGE,
    TYPE_VIDEO,
    TYPE_TEXT,
    TYPE_NUMBER,
    TYPE_LIST,
    TYPE_DICT,
    TYPE_BOOLEAN,
    TYPE_NONE,
    TYPE_UNKNOWN,
    ROUTE_DEFAULT,
    ROUTE_FALLBACK,
)


def test_inspector_image():
    """A list of numbers is treated as IMAGE with shape [len]."""
    label, shape = psn_inspect_type([1.0, 2.0, 3.0])
    assert label == TYPE_IMAGE
    assert shape == [3]


def test_inspector_video():
    """A list of dicts is treated as VIDEO with shape [len]."""
    frames = [{"frame": 0}, {"frame": 1}]
    label, shape = psn_inspect_type(frames)
    assert label == TYPE_VIDEO
    assert shape == [2]


def test_inspector_text_and_number():
    """Strings map to TEXT, numbers to NUMBER, both with empty shape."""
    assert psn_inspect_type("hello") == (TYPE_TEXT, [])
    assert psn_inspect_type(42) == (TYPE_NUMBER, [])
    assert psn_inspect_type(3.14) == (TYPE_NUMBER, [])


def test_inspector_none_bool_dict_list():
    """Edge cases: None, bool, dict, empty list, unknown type."""
    assert psn_inspect_type(None) == (TYPE_NONE, [])
    assert psn_inspect_type(True) == (TYPE_BOOLEAN, [])
    assert psn_inspect_type({"a": 1}) == (TYPE_DICT, [1])
    assert psn_inspect_type([]) == (TYPE_LIST, [0])
    assert psn_inspect_type(object()) == (TYPE_UNKNOWN, [])


def test_router_routes_image_and_video_to_different_pipelines():
    """Image and video data go to different route ids."""
    route_map = json.dumps({
        TYPE_IMAGE: "image_pipeline",
        TYPE_VIDEO: "video_pipeline",
        ROUTE_DEFAULT: "generic_pipeline",
    })
    routed_img, route_img, err_img = psn_route(TYPE_IMAGE, [1, 2, 3], route_map)
    routed_vid, route_vid, err_vid = psn_route(TYPE_VIDEO, [{"f": 0}], route_map)
    assert err_img == "" and err_vid == ""
    assert route_img == "image_pipeline"
    assert route_vid == "video_pipeline"
    assert routed_img == [1, 2, 3]
    assert routed_vid == [{"f": 0}]


def test_router_fallback_when_type_not_mapped():
    """When the type is not in the map and no default, use fallback."""
    route_map = json.dumps({TYPE_IMAGE: "image_pipeline"})
    routed, route_id, err = psn_route(TYPE_TEXT, "hello", route_map)
    assert err == ""
    assert route_id == ROUTE_FALLBACK
    assert routed == "hello"


def test_router_uses_default_when_type_not_mapped():
    """When the type is not in the map but default exists, use default."""
    route_map = json.dumps({
        TYPE_IMAGE: "image_pipeline",
        ROUTE_DEFAULT: "generic_pipeline",
    })
    routed, route_id, err = psn_route(TYPE_TEXT, "hello", route_map)
    assert err == ""
    assert route_id == "generic_pipeline"
    assert routed == "hello"


def test_router_invalid_json_returns_fallback():
    """Invalid JSON route map returns fallback route and error."""
    routed, route_id, err = psn_route(TYPE_IMAGE, [1, 2], "not json")
    assert route_id == ROUTE_FALLBACK
    assert routed is None
    assert "invalid JSON" in err


def test_router_unknown_key_rejected():
    """A route map with an unknown key is rejected."""
    route_map = json.dumps({"BAD_KEY": "some_route"})
    ok, route_dict, err = psn_validate_route_map(route_map)
    assert ok is False
    assert "unknown route key" in err


def test_router_non_string_value_rejected():
    """A route map with a non-string value is rejected."""
    route_map = json.dumps({TYPE_IMAGE: 123})
    ok, route_dict, err = psn_validate_route_map(route_map)
    assert ok is False
    assert "must be a string" in err


def test_node_inspector_run():
    """PSN_Type_Inspector.run returns (label, shape)."""
    node = PSN_Type_Inspector()
    label, shape = node.run([1.0, 2.0])
    assert label == TYPE_IMAGE
    assert shape == [2]


def test_node_router_run():
    """PSN_Pipeline_Router.run returns (routed_data, route_id)."""
    node = PSN_Pipeline_Router()
    route_map = json.dumps({TYPE_IMAGE: "img_pipe", ROUTE_DEFAULT: "def_pipe"})
    routed, route_id = node.run(TYPE_IMAGE, [1, 2, 3], route_map)
    assert routed == [1, 2, 3]
    assert route_id == "img_pipe"


def test_node_router_run_fallback():
    """PSN_Pipeline_Router.run returns fallback route for unmapped type."""
    node = PSN_Pipeline_Router()
    route_map = json.dumps({TYPE_IMAGE: "img_pipe"})
    routed, route_id = node.run(TYPE_TEXT, "hi", route_map)
    assert routed == "hi"
    assert route_id == ROUTE_FALLBACK
