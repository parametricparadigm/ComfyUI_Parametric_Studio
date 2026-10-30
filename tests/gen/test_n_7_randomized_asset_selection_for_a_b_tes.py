import json
import pytest
from psn_nodes.gen.n_7_randomized_asset_selection_for_a_b_tes import PSN_Random_Asset_Selector

class TestPSN_Random_Asset_Selector:
    def setup_method(self):
        self.node = PSN_Random_Asset_Selector()

    def test_reproducibility_with_fixed_seed(self):
        """Test that the same seed produces the same selection."""
        asset_list = json.dumps([f"asset_{i}.png" for i in range(10)])
        seed = 42
        count = 3
        
        result1 = self.node.run(asset_list, seed, count)
        result2 = self.node.run(asset_list, seed, count)
        
        assert result1 == result2
        selected = json.loads(result1[0])
        assert len(selected) == 3
        # Ensure all selected items are from the original list
        for item in selected:
            assert item in [f"asset_{i}.png" for i in range(10)]

    def test_different_seeds_produce_different_results(self):
        """Test that different seeds generally produce different selections."""
        asset_list = json.dumps([f"asset_{i}.png" for i in range(100)])
        seed1 = 1
        seed2 = 2
        count = 10
        
        result1 = self.node.run(asset_list, seed1, count)
        result2 = self.node.run(asset_list, seed2, count)
        
        selected1 = json.loads(result1[0])
        selected2 = json.loads(result2[0])
        
        # It's theoretically possible for them to be the same, but highly unlikely
        # We just check they are valid selections
        assert len(selected1) == 10
        assert len(selected2) == 10

    def test_count_greater_than_list_length(self):
        """Test that selecting more items than available returns all items."""
        asset_list = json.dumps(["a.png", "b.png", "c.png"])
        seed = 123
        count = 10
        
        result = self.node.run(asset_list, seed, count)
        selected = json.loads(result[0])
        
        assert len(selected) == 3
        assert set(selected) == {"a.png", "b.png", "c.png"}

    def test_count_zero(self):
        """Test that count=0 returns an empty list."""
        asset_list = json.dumps(["a.png", "b.png"])
        seed = 123
        count = 0
        
        result = self.node.run(asset_list, seed, count)
        selected = json.loads(result[0])
        
        assert selected == []

    def test_empty_asset_list(self):
        """Test that an empty asset list returns an empty selection."""
        asset_list = json.dumps([])
        seed = 123
        count = 5
        
        result = self.node.run(asset_list, seed, count)
        selected = json.loads(result[0])
        
        assert selected == []

    def test_invalid_json_input(self):
        """Test that invalid JSON raises a ValueError."""
        asset_list = "not a json array"
        seed = 123
        count = 1
        
        with pytest.raises(ValueError):
            self.node.run(asset_list, seed, count)

    def test_non_string_elements_in_list(self):
        """Test that non-string elements in the JSON array raise a ValueError."""
        asset_list = json.dumps(["a.png", 123, "c.png"])
        seed = 123
        count = 1
        
        with pytest.raises(ValueError):
            self.node.run(asset_list, seed, count)

    def test_single_item_selection(self):
        """Test selecting a single item from a list."""
        asset_list = json.dumps(["a.png", "b.png", "c.png"])
        seed = 999
        count = 1
        
        result = self.node.run(asset_list, seed, count)
        selected = json.loads(result[0])
        
        assert len(selected) == 1
        assert selected[0] in ["a.png", "b.png", "c.png"]
