"""Tests for psn_nodes.gen.n_10_audio_parameter_sweep_visualization."""

import pytest

from psn_nodes.gen.n_10_audio_parameter_sweep_visualization import (
    PSN_Audio_Sweep_Config,
    PSN_Audio_Sweep_Plan,
    PSN_Audio_Waveform_Layout,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


def test_sweep_config_valid():
    node = PSN_Audio_Sweep_Config()
    (config,) = node.run("steps", "1,2,3", "cfg", "0.5,1.0")
    assert config["x_param"] == "steps"
    assert config["x_values"] == [1.0, 2.0, 3.0]
    assert config["y_param"] == "cfg"
    assert config["y_values"] == [0.5, 1.0]


def test_sweep_config_bad_param():
    node = PSN_Audio_Sweep_Config()
    with pytest.raises(ValueError, match="unknown parameter"):
        node.run("bogus", "1,2", "cfg", "0.5")


def test_sweep_config_non_numeric_values():
    node = PSN_Audio_Sweep_Config()
    with pytest.raises(ValueError, match="non-numeric"):
        node.run("steps", "1,abc,3", "cfg", "0.5")


def test_sweep_config_out_of_range():
    node = PSN_Audio_Sweep_Config()
    with pytest.raises(ValueError, match="out of range"):
        node.run("steps", "1,99999", "cfg", "0.5")


def test_sweep_plan_expands_grid():
    config = {
        "x_param": "steps",
        "x_values": [1.0, 2.0],
        "y_param": "cfg",
        "y_values": [0.5, 1.0],
    }
    node = PSN_Audio_Sweep_Plan()
    (combinations, metadata_list) = node.run(config)
    assert len(combinations) == 4
    assert len(metadata_list) == 4
    assert combinations[0] == ("steps", 1.0, "cfg", 0.5)
    assert combinations[3] == ("steps", 2.0, "cfg", 1.0)
    assert metadata_list[0] == "steps=1.0 cfg=0.5"


def test_sweep_plan_empty_values():
    config = {
        "x_param": "steps",
        "x_values": [],
        "y_param": "cfg",
        "y_values": [0.5],
    }
    node = PSN_Audio_Sweep_Plan()
    with pytest.raises(ValueError, match="non-empty"):
        node.run(config)


def test_waveform_layout_basic():
    node = PSN_Audio_Waveform_Layout()
    (cols, rows, total_cells, cell_rects) = node.run(
        clip_count=4, cols=2, rows=2, canvas_w=100, canvas_h=100)
    assert cols == 2
    assert rows == 2
    assert total_cells == 4
    assert len(cell_rects) == 4
    # Each rect is (x, y, w, h)
    for rect in cell_rects:
        assert len(rect) == 4
        x, y, w, h = rect
        assert w >= 1 and h >= 1


def test_waveform_layout_too_many_clips():
    node = PSN_Audio_Waveform_Layout()
    with pytest.raises(ValueError, match="exceeds grid capacity"):
        node.run(clip_count=5, cols=2, rows=2, canvas_w=100, canvas_h=100)


def test_waveform_layout_single_cell():
    node = PSN_Audio_Waveform_Layout()
    (cols, rows, total_cells, cell_rects) = node.run(
        clip_count=1, cols=1, rows=1, canvas_w=50, canvas_h=50)
    assert total_cells == 1
    assert len(cell_rects) == 1
    x, y, w, h = cell_rects[0]
    assert x == 0 and y == 0
    assert w == 50 and h == 50


def test_node_mappings_present():
    assert "PSN_Audio_Sweep_Config" in NODE_CLASS_MAPPINGS
    assert "PSN_Audio_Sweep_Plan" in NODE_CLASS_MAPPINGS
    assert "PSN_Audio_Waveform_Layout" in NODE_CLASS_MAPPINGS
    assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Audio_Sweep_Config"] == "Audio Sweep Config"
