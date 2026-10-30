"""Tests for PSN_GlobalSeedBroadcaster module."""

import pytest
from psn_nodes.gen.psn_globalseedbroadcaster import (
    PSN_GlobalSeedBroadcaster,
    psn_broadcast_seed,
    psn_seed_hash,
    _MODES,
)


class TestPsnSeedHash:
    """Tests for the psn_seed_hash helper function."""
    
    def test_psn_seed_hash_deterministic(self):
        """Same seed always produces the same hash."""
        h1 = psn_seed_hash(123)
        h2 = psn_seed_hash(123)
        assert h1 == h2
    
    def test_psn_seed_hash_different_seeds_different_hashes(self):
        """Different seeds produce different hashes."""
        h1 = psn_seed_hash(123)
        h2 = psn_seed_hash(456)
        assert h1 != h2
    
    def test_psn_seed_hash_returns_64_char_hex(self):
        """Hash is a 64-character hexadecimal string."""
        h = psn_seed_hash(0)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)
    
    def test_psn_seed_hash_negative_seed(self):
        """Negative seeds are handled correctly."""
        h = psn_seed_hash(-1)
        assert len(h) == 64
    
    def test_psn_seed_hash_rejects_non_int(self):
        """Non-integer seeds raise TypeError."""
        with pytest.raises(TypeError):
            psn_seed_hash("123")
        with pytest.raises(TypeError):
            psn_seed_hash(123.0)


class TestPsnBroadcastSeed:
    """Tests for the psn_broadcast_seed helper function."""
    
    def test_psn_broadcast_seed_fixed_mode(self):
        """In fixed mode, all downstream nodes receive the exact same seed."""
        downstream = ["KSampler_1", "KSampler_2", "RandomNoise_1"]
        result = psn_broadcast_seed(123, "fixed", downstream)
        assert result == {
            "KSampler_1": 123,
            "KSampler_2": 123,
            "RandomNoise_1": 123,
        }
    
    def test_psn_broadcast_seed_increment_mode(self):
        """In increment mode, each node receives seed + its index."""
        downstream = ["NodeA", "NodeB", "NodeC"]
        result = psn_broadcast_seed(100, "increment", downstream)
        assert result == {
            "NodeA": 100,
            "NodeB": 101,
            "NodeC": 102,
        }
    
    def test_psn_broadcast_seed_empty_downstream(self):
        """Empty downstream list returns empty dict."""
        result = psn_broadcast_seed(42, "fixed", [])
        assert result == {}
    
    def test_psn_broadcast_seed_invalid_mode(self):
        """Invalid mode raises ValueError."""
        with pytest.raises(ValueError):
            psn_broadcast_seed(123, "invalid_mode", ["Node1"])
    
    def test_psn_broadcast_seed_non_int_seed(self):
        """Non-integer seed raises TypeError."""
        with pytest.raises(TypeError):
            psn_broadcast_seed("123", "fixed", ["Node1"])
    
    def test_psn_broadcast_seed_non_list_downstream(self):
        """Non-list downstream raises TypeError."""
        with pytest.raises(TypeError):
            psn_broadcast_seed(123, "fixed", "Node1")


class TestPSNGlobalSeedBroadcaster:
    """Tests for the PSN_GlobalSeedBroadcaster node class."""
    
    def test_psn_global_seed_broadcaster_fixed_mode(self):
        """Node in fixed mode outputs the input seed and its hash."""
        node = PSN_GlobalSeedBroadcaster()
        seed_out, seed_hash = node.run(seed=123, mode="fixed")
        assert seed_out == 123
        assert seed_hash == psn_seed_hash(123)
    
    def test_psn_global_seed_broadcaster_increment_mode(self):
        """Node in increment mode outputs the base seed (per-node offset is in broadcast helper)."""
        node = PSN_GlobalSeedBroadcaster()
        seed_out, seed_hash = node.run(seed=100, mode="increment")
        assert seed_out == 100
        assert seed_hash == psn_seed_hash(100)
    
    def test_psn_global_seed_broadcaster_reproducibility(self):
        """Running the node twice with the same seed produces identical outputs."""
        node = PSN_GlobalSeedBroadcaster()
        out1 = node.run(seed=999, mode="fixed")
        out2 = node.run(seed=999, mode="fixed")
        assert out1 == out2
    
    def test_psn_global_seed_broadcaster_invalid_mode(self):
        """Invalid mode raises ValueError."""
        node = PSN_GlobalSeedBroadcaster()
        with pytest.raises(ValueError):
            node.run(seed=123, mode="bad_mode")
    
    def test_psn_global_seed_broadcaster_non_int_seed(self):
        """Non-integer seed raises TypeError."""
        node = PSN_GlobalSeedBroadcaster()
        with pytest.raises(TypeError):
            node.run(seed="123", mode="fixed")
    
    def test_psn_global_seed_broadcaster_input_types(self):
        """INPUT_TYPES returns the expected structure."""
        it = PSN_GlobalSeedBroadcaster.INPUT_TYPES()
        assert "required" in it
        assert "seed" in it["required"]
        assert "mode" in it["required"]
        # mode is a tuple (list_of_options,) in ComfyUI convention
        assert it["required"]["mode"][0] == list(_MODES)
    
    def test_psn_global_seed_broadcaster_return_types(self):
        """RETURN_TYPES and RETURN_NAMES are correct."""
        assert PSN_GlobalSeedBroadcaster.RETURN_TYPES == ("INT", "STRING")
        assert PSN_GlobalSeedBroadcaster.RETURN_NAMES == ("seed_out", "seed_hash")
    
    def test_psn_global_seed_broadcaster_negative_seed(self):
        """Negative seeds work correctly."""
        node = PSN_GlobalSeedBroadcaster()
        seed_out, seed_hash = node.run(seed=-50, mode="fixed")
        assert seed_out == -50
        assert seed_hash == psn_seed_hash(-50)
