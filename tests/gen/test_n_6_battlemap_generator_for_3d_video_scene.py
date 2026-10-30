"""
Tests for PSN_Battlemap_Generate node.

These tests verify the pure-logic battlemap generation without any GPU, torch,
ComfyUI, or image library dependencies.
"""

import pytest
from psn_nodes.gen.n_6_battlemap_generator_for_3d_video_scene import (
    PSN_Battlemap_Generate,
    _generate_grid_map,
    _generate_terrain_map,
    _generate_urban_map,
    GRID_STYLES
)


class TestPSN_Battlemap_Generate:
    """Test suite for the PSN_Battlemap_Generate node."""
    
    def test_input_types_structure(self):
        """Verify INPUT_TYPES has required fields with correct types."""
        input_types = PSN_Battlemap_Generate.INPUT_TYPES()
        
        assert "required" in input_types
        required = input_types["required"]
        
        assert "width" in required
        assert "height" in required
        assert "cell_size" in required
        assert "style" in required
        assert "seed" in required
        
        # Verify style options
        style_options = required["style"][0]
        assert style_options == GRID_STYLES
        assert "grid" in style_options
        assert "terrain" in style_options
        assert "urban" in style_options
    
    def test_return_types(self):
        """Verify RETURN_TYPES and RETURN_NAMES are correctly defined."""
        assert PSN_Battlemap_Generate.RETURN_TYPES == ("MAP_DATA", "HEIGHTMAP_DATA")
        assert PSN_Battlemap_Generate.RETURN_NAMES == ("map_image", "heightmap")
        assert PSN_Battlemap_Generate.FUNCTION == "run"
        assert PSN_Battlemap_Generate.CATEGORY == "ParametricStudio/Battlemap"
    
    def test_grid_map_generation(self):
        """Test grid map generation produces correct dimensions and structure."""
        node = PSN_Battlemap_Generate()
        map_data, heightmap_data = node.run(width=10, height=10, cell_size=32, style="grid", seed=42)
        
        # Verify dimensions
        assert len(map_data) == 10
        assert len(heightmap_data) == 10
        for row in map_data:
            assert len(row) == 10
        for row in heightmap_data:
            assert len(row) == 10
        
        # Verify map_data contains RGB tuples
        for row in map_data:
            for cell in row:
                assert isinstance(cell, tuple)
                assert len(cell) == 3
                for component in cell:
                    assert 0 <= component <= 255
        
        # Verify heightmap contains floats between 0 and 1
        for row in heightmap_data:
            for value in row:
                assert isinstance(value, float)
                assert 0.0 <= value <= 1.0
        
        # Grid should have uniform height of 0.5
        for row in heightmap_data:
            for value in row:
                assert value == 0.5
    
    def test_terrain_map_generation(self):
        """Test terrain map generation produces valid output."""
        node = PSN_Battlemap_Generate()
        map_data, heightmap_data = node.run(width=10, height=10, cell_size=32, style="terrain", seed=42)
        
        # Verify dimensions
        assert len(map_data) == 10
        assert len(heightmap_data) == 10
        
        # Verify heightmap has variation (not all same value)
        heights = [value for row in heightmap_data for value in row]
        assert len(set(heights)) > 1, "Terrain heightmap should have variation"
        
        # Verify all heights are in valid range
        for value in heights:
            assert 0.0 <= value <= 1.0
    
    def test_urban_map_generation(self):
        """Test urban map generation produces valid output with roads."""
        node = PSN_Battlemap_Generate()
        map_data, heightmap_data = node.run(width=10, height=10, cell_size=32, style="urban", seed=42)
        
        # Verify dimensions
        assert len(map_data) == 10
        assert len(heightmap_data) == 10
        
        # Urban maps should have some low-height cells (roads)
        heights = [value for row in heightmap_data for value in row]
        assert any(h < 0.2 for h in heights), "Urban map should have roads (low height)"
    
    def test_deterministic_output(self):
        """Test that same seed produces identical output."""
        node = PSN_Battlemap_Generate()
        
        map1, height1 = node.run(width=10, height=10, cell_size=32, style="terrain", seed=123)
        map2, height2 = node.run(width=10, height=10, cell_size=32, style="terrain", seed=123)
        
        assert map1 == map2
        assert height1 == height2
    
    def test_different_seeds_produce_different_output(self):
        """Test that different seeds produce different terrain output."""
        node = PSN_Battlemap_Generate()
        
        map1, height1 = node.run(width=10, height=10, cell_size=32, style="terrain", seed=1)
        map2, height2 = node.run(width=10, height=10, cell_size=32, style="terrain", seed=2)
        
        # Terrain should differ with different seeds
        assert height1 != height2, "Different seeds should produce different terrain"
    
    def test_invalid_width_raises_error(self):
        """Test that invalid width raises ValueError."""
        node = PSN_Battlemap_Generate()
        with pytest.raises(ValueError, match="Width and height must be at least 1"):
            node.run(width=0, height=10, cell_size=32, style="grid", seed=42)
    
    def test_invalid_height_raises_error(self):
        """Test that invalid height raises ValueError."""
        node = PSN_Battlemap_Generate()
        with pytest.raises(ValueError, match="Width and height must be at least 1"):
            node.run(width=10, height=0, cell_size=32, style="grid", seed=42)
    
    def test_invalid_cell_size_raises_error(self):
        """Test that invalid cell size raises ValueError."""
        node = PSN_Battlemap_Generate()
        with pytest.raises(ValueError, match="Cell size must be at least 1"):
            node.run(width=10, height=10, cell_size=0, style="grid", seed=42)
    
    def test_invalid_style_raises_error(self):
        """Test that invalid style raises ValueError."""
        node = PSN_Battlemap_Generate()
        with pytest.raises(ValueError, match="Style must be one of"):
            node.run(width=10, height=10, cell_size=32, style="invalid_style", seed=42)
    
    def test_minimal_map_size(self):
        """Test that 1x1 map works correctly."""
        node = PSN_Battlemap_Generate()
        map_data, heightmap_data = node.run(width=1, height=1, cell_size=32, style="grid", seed=42)
        
        assert len(map_data) == 1
        assert len(map_data[0]) == 1
        assert len(heightmap_data) == 1
        assert len(heightmap_data[0]) == 1
        
        # Single cell should be border color
        assert map_data[0][0] == (50, 50, 50)
    
    def test_large_map_dimensions(self):
        """Test that larger maps are generated correctly."""
        node = PSN_Battlemap_Generate()
        map_data, heightmap_data = node.run(width=50, height=50, cell_size=16, style="terrain", seed=42)
        
        assert len(map_data) == 50
        assert len(heightmap_data) == 50
        for row in map_data:
            assert len(row) == 50
        for row in heightmap_data:
            assert len(row) == 50
    
    def test_node_class_mappings(self):
        """Test that NODE_CLASS_MAPPINGS is correctly defined."""
        from psn_nodes.gen.n_6_battlemap_generator_for_3d_video_scene import NODE_CLASS_MAPPINGS
        
        assert "PSN_Battlemap_Generate" in NODE_CLASS_MAPPINGS
        assert NODE_CLASS_MAPPINGS["PSN_Battlemap_Generate"] == PSN_Battlemap_Generate
    
    def test_node_display_name_mappings(self):
        """Test that NODE_DISPLAY_NAME_MAPPINGS is correctly defined."""
        from psn_nodes.gen.n_6_battlemap_generator_for_3d_video_scene import NODE_DISPLAY_NAME_MAPPINGS
        
        assert "PSN_Battlemap_Generate" in NODE_DISPLAY_NAME_MAPPINGS
        assert NODE_DISPLAY_NAME_MAPPINGS["PSN_Battlemap_Generate"] == "Battlemap Generator"
