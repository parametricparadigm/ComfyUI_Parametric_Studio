"""
Tests for psn_nodes.gen.n_8_z_image_specific_xy_plotting
"""

import pytest

from psn_nodes.gen.n_8_z_image_specific_xy_plotting import (
    PSN_ZImage_Plot_Config,
    PSN_ZImage_Grid_Generator,
    PSN_ZImage_Grid_Visualizer,
    _parse_values,
    _build_param_matrix,
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)


class TestParseValues:
    def test_parse_int_values(self):
        result = _parse_values("10,20,30", "steps", True)
        assert result == [10, 20, 30]
        assert all(isinstance(v, int) for v in result)

    def test_parse_float_values(self):
        result = _parse_values("1.5,2.5,3.5", "cfg", True)
        assert result == [1.5, 2.5, 3.5]
        assert all(isinstance(v, float) for v in result)

    def test_parse_out_of_range_raises(self):
        with pytest.raises(ValueError, match="out of range"):
            _parse_values("200", "steps", True)  # max is 100 for z_image_specific

    def test_parse_non_numeric_raises(self):
        with pytest.raises(ValueError, match="Cannot parse"):
            _parse_values("abc", "steps", True)

    def test_parse_empty_string_raises(self):
        with pytest.raises(ValueError, match="empty"):
            _parse_values("", "steps", True)

    def test_parse_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="empty"):
            _parse_values("   ", "cfg", True)

    def test_parse_guidance_range(self):
        # guidance max is 10.0 for z_image_specific
        result = _parse_values("0.0,5.0,10.0", "guidance", True)
        assert result == [0.0, 5.0, 10.0]

    def test_parse_guidance_out_of_range(self):
        with pytest.raises(ValueError, match="out of range"):
            _parse_values("15.0", "guidance", True)


class TestBuildParamMatrix:
    def test_basic_matrix(self):
        matrix = _build_param_matrix("steps", [10, 20], "cfg", [1.0, 2.0])
        assert matrix == [
            "steps=10, cfg=1.0",
            "steps=20, cfg=1.0",
            "steps=10, cfg=2.0",
            "steps=20, cfg=2.0",
        ]

    def test_single_value_matrix(self):
        matrix = _build_param_matrix("steps", [10], "cfg", [1.0])
        assert matrix == ["steps=10, cfg=1.0"]

    def test_matrix_order_row_major(self):
        # y is outer loop, x is inner loop
        matrix = _build_param_matrix("steps", [1, 2], "cfg", [10.0, 20.0])
        assert matrix[0] == "steps=1, cfg=10.0"
        assert matrix[1] == "steps=2, cfg=10.0"
        assert matrix[2] == "steps=1, cfg=20.0"
        assert matrix[3] == "steps=2, cfg=20.0"


class TestPSN_ZImage_Plot_Config:
    def setup_method(self):
        self.node = PSN_ZImage_Plot_Config()

    def test_basic_config(self):
        config, x_parsed, y_parsed, matrix = self.node.run(
            x_param="steps",
            x_values="10,20",
            y_param="cfg",
            y_values="1.0,2.0",
            z_image_specific=True,
        )
        assert config["x_param"] == "steps"
        assert config["y_param"] == "cfg"
        assert config["z_image_specific"] is True
        assert config["x_values"] == [10, 20]
        assert config["y_values"] == [1.0, 2.0]
        assert config["grid_size"] == (2, 2)
        assert len(matrix) == 4

    def test_z_image_specific_defaults_applied(self):
        config, _, _, _ = self.node.run(
            x_param="steps",
            x_values="10",
            y_param="guidance",
            y_values="1.0",
            z_image_specific=True,
        )
        assert config["defaults"]["x"]["default"] == 20
        assert config["defaults"]["y"]["default"] == 2.0

    def test_non_z_image_specific_defaults(self):
        config, _, _, _ = self.node.run(
            x_param="steps",
            x_values="10",
            y_param="cfg",
            y_values="1.0",
            z_image_specific=False,
        )
        assert config["defaults"]["x"]["default"] == 20
        assert config["defaults"]["y"]["default"] == 7.0

    def test_invalid_x_param_raises(self):
        with pytest.raises(ValueError):
            self.node.run(
                x_param="invalid_param",
                x_values="10",
                y_param="cfg",
                y_values="1.0",
                z_image_specific=True,
            )

    def test_bad_x_values_raises(self):
        with pytest.raises(ValueError):
            self.node.run(
                x_param="steps",
                x_values="not_a_number",
                y_param="cfg",
                y_values="1.0",
                z_image_specific=True,
            )


class TestPSN_ZImage_Grid_Generator:
    def setup_method(self):
        self.node = PSN_ZImage_Grid_Generator()

    def test_basic_generation(self):
        config = {
            "x_param": "steps",
            "x_values": [10, 20],
            "y_param": "cfg",
            "y_values": [1.0, 2.0],
            "z_image_specific": True,
            "param_matrix": [
                "steps=10, cfg=1.0",
                "steps=20, cfg=1.0",
                "steps=10, cfg=2.0",
                "steps=20, cfg=2.0",
            ],
            "grid_size": (2, 2),
        }
        placeholders, matrix = self.node.run(
            plot_config=config,
            prompt="test prompt",
            negative_prompt="bad",
            width=512,
            height=512,
        )
        assert len(placeholders) == 4
        assert len(matrix) == 4
        assert placeholders[0]["label"] == "steps=10, cfg=1.0"
        assert placeholders[0]["prompt"] == "test prompt"
        assert placeholders[0]["width"] == 512

    def test_empty_matrix_raises(self):
        config = {"param_matrix": []}
        with pytest.raises(ValueError, match="empty param_matrix"):
            self.node.run(
                plot_config=config,
                prompt="test",
                negative_prompt="",
                width=512,
                height=512,
            )

    def test_non_dict_config_raises(self):
        with pytest.raises(TypeError):
            self.node.run(
                plot_config="not a dict",
                prompt="test",
                negative_prompt="",
                width=512,
                height=512,
            )


class TestPSN_ZImage_Grid_Visualizer:
    def setup_method(self):
        self.node = PSN_ZImage_Grid_Visualizer()

    def test_basic_summary(self):
        placeholders = [
            {"index": 0, "label": "steps=10, cfg=1.0"},
            {"index": 1, "label": "steps=20, cfg=1.0"},
        ]
        matrix = ["steps=10, cfg=1.0", "steps=20, cfg=1.0"]
        (summary,) = self.node.run(grid_placeholders=placeholders, param_matrix=matrix)
        assert "2 cells" in summary
        assert "steps=10, cfg=1.0" in summary

    def test_length_mismatch_raises(self):
        placeholders = [{"index": 0, "label": "a"}]
        matrix = ["a", "b"]
        with pytest.raises(ValueError, match="Length mismatch"):
            self.node.run(grid_placeholders=placeholders, param_matrix=matrix)

    def test_empty_grid(self):
        (summary,) = self.node.run(grid_placeholders=[], param_matrix=[])
        assert summary == "Empty grid."

    def test_non_list_placeholders_raises(self):
        with pytest.raises(TypeError):
            self.node.run(grid_placeholders="not a list", param_matrix=[])

    def test_non_list_matrix_raises(self):
        with pytest.raises(TypeError):
            self.node.run(grid_placeholders=[], param_matrix="not a list")


class TestNodeMappings:
    def test_node_class_mappings(self):
        assert "PSN_ZImage_Plot_Config" in NODE_CLASS_MAPPINGS
        assert "PSN_ZImage_Grid_Generator" in NODE_CLASS_MAPPINGS
        assert "PSN_ZImage_Grid_Visualizer" in NODE_CLASS_MAPPINGS

    def test_display_name_mappings(self):
        assert NODE_DISPLAY_NAME_MAPPINGS["PSN_ZImage_Plot_Config"] == "Z-Image Plot Config"
        assert NODE_DISPLAY_NAME_MAPPINGS["PSN_ZImage_Grid_Generator"] == "Z-Image Grid Generator"
        assert NODE_DISPLAY_NAME_MAPPINGS["PSN_ZImage_Grid_Visualizer"] == "Z-Image Grid Visualizer"

    def test_input_types_structure(self):
        it = PSN_ZImage_Plot_Config.INPUT_TYPES()
        assert "required" in it
        assert "x_param" in it["required"]
        assert "x_values" in it["required"]
        assert "y_param" in it["required"]
        assert "y_values" in it["required"]
        assert "z_image_specific" in it["required"]
