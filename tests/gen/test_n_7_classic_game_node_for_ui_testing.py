import pytest

from psn_nodes.gen.n_7_classic_game_node_for_ui_testing import (
    PSN_Classic_Game_UI,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    _validate_game,
    _validate_dims,
    _make_handle,
)


def test_node_registered_and_named():
    assert "PSN_Classic_Game_UI" in NODE_CLASS_MAPPINGS
    assert NODE_CLASS_MAPPINGS["PSN_Classic_Game_UI"] is PSN_Classic_Game_UI
    assert "PSN_Classic_Game_UI" in NODE_DISPLAY_NAME_MAPPINGS


def test_input_types_shape():
    spec = PSN_Classic_Game_UI.INPUT_TYPES()
    assert "required" in spec
    req = spec["required"]
    assert "game_type" in req
    assert "width" in req
    assert "height" in req
    # game_type is a combo of the four supported games
    assert set(req["game_type"][0]) == {"tetris", "snake", "pacman", "checkers"}


def test_valid_tetris_produces_handle_and_zero_score():
    node = PSN_Classic_Game_UI()
    handle, score, ok = node.run("tetris", 256, 256)
    assert ok is True
    assert score == 0
    assert isinstance(handle, str)
    assert handle.startswith("ui_tetris_")
    assert len(handle) > len("ui_tetris_")


def test_handle_is_deterministic_and_param_sensitive():
    node = PSN_Classic_Game_UI()
    h1, _, _ = node.run("snake", 320, 240)
    h2, _, _ = node.run("snake", 320, 240)
    h3, _, _ = node.run("snake", 321, 240)
    assert h1 == h2
    assert h1 != h3


def test_case_and_whitespace_insensitive_game_type():
    node = PSN_Classic_Game_UI()
    h1, _, ok1 = node.run("  TETRIS ", 128, 128)
    h2, _, ok2 = node.run("tetris", 128, 128)
    assert ok1 is True and ok2 is True
    assert h1 == h2


def test_unknown_game_type_rejected():
    node = PSN_Classic_Game_UI()
    handle, score, ok = node.run("chess", 256, 256)
    assert ok is False
    assert handle == ""
    assert score == 0


def test_non_string_game_type_rejected():
    ok, game, why = _validate_game(123)
    assert ok is False
    assert game is None
    assert "string" in why


def test_width_out_of_range_rejected():
    node = PSN_Classic_Game_UI()
    handle, score, ok = node.run("tetris", 0, 256)
    assert ok is False
    assert handle == ""
    handle2, _, ok2 = node.run("tetris", 5000, 256)
    assert ok2 is False


def test_height_out_of_range_rejected():
    node = PSN_Classic_Game_UI()
    _, _, ok = node.run("snake", 256, 99999)
    assert ok is False


def test_bool_not_accepted_as_int_dimension():
    # bool is a subclass of int; we explicitly reject it.
    ok, w, h, why = _validate_dims(True, 256)
    assert ok is False
    assert "integer" in why


def test_non_int_dimension_rejected():
    ok, w, h, why = _validate_dims(256.5, 256)
    assert ok is False
    assert "integer" in why


def test_make_handle_stable_for_same_params():
    a = _make_handle("pacman", 100, 100)
    b = _make_handle("pacman", 100, 100)
    assert a == b
    assert a.startswith("ui_pacman_")


def test_all_supported_games_accepted():
    node = PSN_Classic_Game_UI()
    for g in ("tetris", "snake", "pacman", "checkers"):
        handle, score, ok = node.run(g, 200, 200)
        assert ok is True
        assert score == 0
        assert handle.startswith("ui_%s_" % g)
