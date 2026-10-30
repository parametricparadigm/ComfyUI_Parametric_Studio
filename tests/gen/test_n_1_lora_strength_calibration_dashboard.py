"""
Tests for psn_nodes.gen.n_1_lora_strength_calibration_dashboard
"""

import pytest
from psn_nodes.gen.n_1_lora_strength_calibration_dashboard import (
    PSN_LoRA_Sweep_Config,
    PSN_LoRA_Grid_Generator,
    PSN_LoRA_Grid_Assembler,
    _compute_strength_values,
    _validate_strength_range,
    _build_metadata,
)


class TestComputeStrengthValues:
    def test_single_step_returns_min(self):
        vals = _compute_strength_values(0.5, 1.0, 1)
        assert vals == [0.5]

    def test_two_steps_returns_min_and_max(self):
        vals = _compute_strength_values(0.0, 1.0, 2)
        assert vals == [0.0, 1.0]

    def test_five_steps_linear_interpolation(self):
        vals = _compute_strength_values(0.0, 1.0, 5)
        assert len(vals) == 5
        assert vals[0] == pytest.approx(0.0)
        assert vals[-1] == pytest.approx(1.0)
        assert vals[1] == pytest.approx(0.25)
        assert vals[2] == pytest.approx(0.5)
        assert vals[3] == pytest.approx(0.75)

    def test_negative_range(self):
        vals = _compute_strength_values(-1.0, 1.0, 3)
        assert vals == [-1.0, 0.0, 1.0]

    def test_zero_steps_raises(self):
        with pytest.raises(ValueError, match="steps must be >= 1"):
            _compute_strength_values(0.0, 1.0, 0)

    def test_non_integer_steps_raises(self):
        with pytest.raises(ValueError, match="steps must be an integer"):
            _compute_strength_values(0.0, 1.0, 2.5)


class TestValidateStrengthRange:
    def test_valid_range(self):
        assert _validate_strength_range(0.0, 1.0) is True

    def test_equal_range(self):
        assert _validate_strength_range(0.5, 0.5) is True

    def test_min_greater_than_max_raises(self):
        with pytest.raises(ValueError, match="strength_min must be <= strength_max"):
            _validate_strength_range(1.0, 0.0)

    def test_non_numeric_min_raises(self):
        with pytest.raises(ValueError, match="strength_min must be a number"):
            _validate_strength_range("a", 1.0)

    def test_non_numeric_max_raises(self):
        with pytest.raises(ValueError, match="strength_max must be a number"):
            _validate_strength_range(0.0, "b")


class TestLoRA_Sweep_Config:
    def test_basic_config(self):
        node = PSN_LoRA_Sweep_Config()
        (config,) = node.run(
            strength_min=0.0,
            strength_max=1.0,
            steps=5,
            seed=42,
            prompt="a cat",
            negative_prompt="blurry",
        )
        assert config["strength_min"] == 0.0
        assert config["strength_max"] == 1.0
        assert config["steps"] == 5
        assert config["seed"] == 42
        assert config["prompt"] == "a cat"
        assert config["negative_prompt"] == "blurry"
        assert len(config["strength_values"]) == 5
        assert config["strength_values"][0] == pytest.approx(0.0)
        assert config["strength_values"][-1] == pytest.approx(1.0)

    def test_single_step_config(self):
        node = PSN_LoRA_Sweep_Config()
        (config,) = node.run(
            strength_min=0.7,
            strength_max=0.7,
            steps=1,
            seed=0,
            prompt="test",
            negative_prompt="",
        )
        assert config["strength_values"] == [0.7]

    def test_invalid_range_raises(self):
        node = PSN_LoRA_Sweep_Config()
        with pytest.raises(ValueError, match="strength_min must be <= strength_max"):
            node.run(
                strength_min=1.0,
                strength_max=0.0,
                steps=3,
                seed=0,
                prompt="x",
                negative_prompt="",
            )

    def test_optional_models_stored(self):
        node = PSN_LoRA_Sweep_Config()
        fake_lora = {"name": "test_lora"}
        fake_ckpt = {"name": "test_ckpt"}
        (config,) = node.run(
            strength_min=0.0,
            strength_max=1.0,
            steps=2,
            seed=1,
            prompt="p",
            negative_prompt="n",
            lora_model=fake_lora,
            checkpoint=fake_ckpt,
        )
        assert config["lora_model"] is fake_lora
        assert config["checkpoint"] is fake_ckpt


class TestLoRA_Grid_Generator:
    def _make_config(self, strengths):
        return {
            "strength_min": strengths[0],
            "strength_max": strengths[-1],
            "steps": len(strengths),
            "strength_values": strengths,
            "seed": 99,
            "prompt": "hello",
            "negative_prompt": "bad",
        }

    def test_2x2_grid(self):
        node = PSN_LoRA_Grid_Generator()
        config = self._make_config([0.0, 0.5, 1.0, 1.5])
        cells, metas = node.run(config, grid_cols=2, grid_rows=2)
        assert len(cells) == 4
        assert len(metas) == 4
        assert cells[0]["row"] == 0 and cells[0]["col"] == 0
        assert cells[1]["row"] == 0 and cells[1]["col"] == 1
        assert cells[2]["row"] == 1 and cells[2]["col"] == 0
        assert cells[3]["row"] == 1 and cells[3]["col"] == 1
        assert cells[0]["strength"] == pytest.approx(0.0)
        assert cells[3]["strength"] == pytest.approx(1.5)
        assert "strength=0.0000" in metas[0]
        assert "seed=99" in metas[0]

    def test_more_cells_than_strengths_cycles(self):
        node = PSN_LoRA_Grid_Generator()
        config = self._make_config([0.0, 1.0])
        cells, metas = node.run(config, grid_cols=3, grid_rows=2)
        assert len(cells) == 6
        # Cycles: 0.0, 1.0, 0.0, 1.0, 0.0, 1.0
        assert cells[0]["strength"] == pytest.approx(0.0)
        assert cells[1]["strength"] == pytest.approx(1.0)
        assert cells[2]["strength"] == pytest.approx(0.0)

    def test_invalid_grid_cols_raises(self):
        node = PSN_LoRA_Grid_Generator()
        config = self._make_config([0.0, 1.0])
        with pytest.raises(ValueError, match="grid_cols must be a positive integer"):
            node.run(config, grid_cols=0, grid_rows=2)

    def test_invalid_grid_rows_raises(self):
        node = PSN_LoRA_Grid_Generator()
        config = self._make_config([0.0, 1.0])
        with pytest.raises(ValueError, match="grid_rows must be a positive integer"):
            node.run(config, grid_cols=2, grid_rows=-1)

    def test_missing_strength_values_raises(self):
        node = PSN_LoRA_Grid_Generator()
        bad_config = {"seed": 1, "prompt": "x"}
        with pytest.raises(ValueError, match="missing 'strength_values'"):
            node.run(bad_config, grid_cols=1, grid_rows=1)

    def test_non_dict_config_raises(self):
        node = PSN_LoRA_Grid_Generator()
        with pytest.raises(ValueError, match="sweep_config must be a dict"):
            node.run("not a dict", grid_cols=1, grid_rows=1)


class TestLoRA_Grid_Assembler:
    def _make_cells(self, cols, rows):
        cells = []
        for idx in range(cols * rows):
            cells.append({
                "strength": 0.5,
                "row": idx // cols,
                "col": idx % cols,
                "index": idx,
            })
        return cells

    def test_2x2_grid_dimensions(self):
        node = PSN_LoRA_Grid_Assembler()
        cells = self._make_cells(2, 2)
        metas = ["m0", "m1", "m2", "m3"]
        gw, gh, labels = node.run(
            cell_descriptors=cells,
            metadata_list=metas,
            grid_cols=2,
            grid_rows=2,
            cell_width=512,
            cell_height=512,
            label_font_size=24,
        )
        assert gw == 1024
        assert gh == 1024
        assert len(labels) == 4
        assert labels[0]["x"] == 4
        assert labels[0]["y"] == 4
        assert labels[1]["x"] == 512 + 4
        assert labels[1]["y"] == 4
        assert labels[2]["x"] == 4
        assert labels[2]["y"] == 512 + 4
        assert labels[3]["x"] == 512 + 4
        assert labels[3]["y"] == 512 + 4
        assert labels[0]["text"] == "m0"
        assert labels[0]["font_size"] == 24

    def test_3x2_grid_dimensions(self):
        node = PSN_LoRA_Grid_Assembler()
        cells = self._make_cells(3, 2)
        metas = [f"meta_{i}" for i in range(6)]
        gw, gh, labels = node.run(
            cell_descriptors=cells,
            metadata_list=metas,
            grid_cols=3,
            grid_rows=2,
            cell_width=256,
            cell_height=128,
            label_font_size=16,
        )
        assert gw == 768
        assert gh == 256
        assert len(labels) == 6

    def test_mismatched_cell_count_raises(self):
        node = PSN_LoRA_Grid_Assembler()
        cells = self._make_cells(2, 2)  # 4 cells
        metas = ["a", "b", "c"]  # only 3
        with pytest.raises(ValueError, match="does not match"):
            node.run(
                cell_descriptors=cells,
                metadata_list=metas,
                grid_cols=2,
                grid_rows=2,
                cell_width=100,
                cell_height=100,
                label_font_size=10,
            )

    def test_invalid_cell_width_raises(self):
        node = PSN_LoRA_Grid_Assembler()
        cells = self._make_cells(1, 1)
        with pytest.raises(ValueError, match="cell_width must be a positive integer"):
            node.run(
                cell_descriptors=cells,
                metadata_list=["x"],
                grid_cols=1,
                grid_rows=1,
                cell_width=0,
                cell_height=100,
                label_font_size=10,
            )

    def test_invalid_label_font_size_raises(self):
        node = PSN_LoRA_Grid_Assembler()
        cells = self._make_cells(1, 1)
        with pytest.raises(ValueError, match="label_font_size must be a positive integer"):
            node.run(
                cell_descriptors=cells,
                metadata_list=["x"],
                grid_cols=1,
                grid_rows=1,
                cell_width=100,
                cell_height=100,
                label_font_size=0,
            )

    def test_non_list_descriptors_raises(self):
        node = PSN_LoRA_Grid_Assembler()
        with pytest.raises(ValueError, match="cell_descriptors must be a list"):
            node.run(
                cell_descriptors="not a list",
                metadata_list=["x"],
                grid_cols=1,
                grid_rows=1,
                cell_width=100,
                cell_height=100,
                label_font_size=10,
            )


class TestBuildMetadata:
    def test_metadata_format(self):
        meta = _build_metadata(0.75, 1, 2, 42, "a cat")
        assert "strength=0.7500" in meta
        assert "row=1" in meta
        assert "col=2" in meta
        assert "seed=42" in meta
        assert "prompt='a cat'" in meta

    def test_metadata_with_special_chars(self):
        meta = _build_metadata(1.0, 0, 0, 0, "hello \"world\"")
        assert "prompt=" in meta
